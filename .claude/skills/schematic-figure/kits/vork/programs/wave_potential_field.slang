// kits/vork/programs/wave_potential_field.slang
// Reusable Scientific Wave Interference & Potential Field Shader for schematic-figure

struct FieldSource {
    float3 position;   // World coordinates (x, y, z)
    float  amplitude;  // Source strength A_i (or charge q_i for potentials)
    float  wavelength; // lambda_i (or softening radius a_i in Mode 1)
    float  phase;      // phi_i in radians
};

struct FieldParams {
    int    mode;             // 0 = Wave Interference, 1 = Electrostatic/Potential Well, 2 = Optical Lattice
    int    num_sources;      // Active sources (up to 8)
    float  time;             // Animation phase t
    float  damping;          // Spatial attenuation alpha (e^(-alpha * r))
    float  contour_spacing;  // Equipotential line interval (0 = off, e.g. 0.25)
    float  contour_strength; // Darkness of iso-contour lines [0..1]
    float  normal_scale;     // 3D relief shading strength from analytic gradient
    float  envelope_radius;  // Gaussian window falloff radius (0 = infinite plane)
    FieldSource sources[8];
};

// 1. Scientific Diverging Colormap (CoolWarm: Cobalt Blue -> Paper White -> Carmine Red)
float3 colormap_coolwarm(float u) {
    float x = clamp(u, -1.0, 1.0);
    const float3 neg_col  = float3(0.08, 0.28, 0.68);
    const float3 zero_col = float3(0.96, 0.96, 0.95);
    const float3 pos_col  = float3(0.75, 0.12, 0.16);

    if (x < 0.0) {
        return lerp(zero_col, neg_col, smoothstep(0.0, 1.0, -x));
    } else {
        return lerp(zero_col, pos_col, smoothstep(0.0, 1.0, x));
    }
}

// 2. Analytic Field & Spatial Gradient Evaluator: returns float3(psi, dpsi/dx, dpsi/dz)
float3 evaluate_scientific_field(float2 xz, FieldParams params) {
    float  psi = 0.0;
    float2 grad = float2(0.0, 0.0);
    const float TWO_PI = 6.28318530718;
    const float EPS = 1e-4;

    if (params.mode == 0) {
        // MODE 0: Superposition of Travelling Cylindrical/Spherical Waves
        [ForceUnroll]
        for (int i = 0; i < 8; ++i) {
            if (i >= params.num_sources) break;
            FieldSource s = params.sources[i];

            float2 d = xz - s.position.xz;
            float  r = sqrt(dot(d, d) + EPS);
            float2 r_hat = d / r;

            float k = TWO_PI / max(s.wavelength, 1e-3);
            float theta = k * r - params.time + s.phase;
            float env = exp(-params.damping * r) / sqrt(1.0 + 0.5 * r);

            float cos_t = cos(theta);
            float sin_t = sin(theta);

            psi += s.amplitude * env * cos_t;

            float dpsi_dr = s.amplitude * env * (-k * sin_t - (params.damping + 0.25 / (1.0 + 0.5 * r)) * cos_t);
            grad += dpsi_dr * r_hat;
        }
    }
    else if (params.mode == 1) {
        // MODE 1: Softened Coulomb / Potential Wells V(r) = sum q_i / sqrt(r^2 + a^2)
        [ForceUnroll]
        for (int i = 0; i < 8; ++i) {
            if (i >= params.num_sources) break;
            FieldSource s = params.sources[i];

            float2 d = xz - s.position.xz;
            float  a = max(s.wavelength, 0.15);
            float  r2_soft = dot(d, d) + a * a;
            float  inv_r = rsqrt(r2_soft);

            psi  += s.amplitude * inv_r;
            grad -= s.amplitude * d * (inv_r * inv_r * inv_r);
        }
    }
    else {
        // MODE 2: 2D Optical Standing-Wave Lattice
        float k = TWO_PI / max(params.sources[0].wavelength, 0.5);
        float cx = cos(k * xz.x);
        float cz = cos(k * xz.y);

        psi = params.sources[0].amplitude * (cx * cx + cz * cz - 1.0);
        grad = params.sources[0].amplitude * float2(-k * sin(2.0 * k * xz.x), -k * sin(2.0 * k * xz.y));
    }

    if (params.envelope_radius > 0.0) {
        float r2 = dot(xz, xz);
        float inv_w2 = 1.0 / (params.envelope_radius * params.envelope_radius);
        float window = exp(-r2 * inv_w2);
        grad = grad * window - psi * window * (2.0 * xz * inv_w2);
        psi *= window;
    }

    return float3(psi, grad.x, grad.y);
}

// 3. Surface Shading Hook
struct ScientificSurfaceOutput {
    float3 base_color;
    float3 world_normal;
    float  specular_roughness;
    float3 emission;
};

ScientificSurfaceOutput shade_field_surface(float3 world_pos, float3 geom_normal, FieldParams params) {
    float3 field = evaluate_scientific_field(world_pos.xz, params);
    float  psi   = field.x;
    float2 grad  = field.yz;

    float3 color = colormap_coolwarm(psi);

    if (params.contour_spacing > 0.0) {
        float scaled_psi = psi / params.contour_spacing;
        float dist_to_line = abs(frac(scaled_psi + 0.5) - 0.5) * params.contour_spacing;
        float grad_mag = max(length(grad), 1e-3);
        float line_width = 0.015 * grad_mag;
        float contour_mask = 1.0 - smoothstep(0.0, line_width, dist_to_line);
        float zero_boost = (abs(psi) < 0.04) ? 1.35 : 1.0;
        color = lerp(color, float3(0.12, 0.14, 0.18), clamp(contour_mask * params.contour_strength * zero_boost, 0.0, 0.85));
    }

    float3 perturbed_normal = normalize(float3(
        -grad.x * params.normal_scale,
         1.0,
        -grad.y * params.normal_scale
    ));

    ScientificSurfaceOutput out_mat;
    out_mat.base_color = color;
    out_mat.world_normal = normalize(lerp(geom_normal, perturbed_normal, 0.85));
    out_mat.specular_roughness = 0.28;
    out_mat.emission = color * (0.08 * smoothstep(0.6, 1.0, abs(psi)));
    return out_mat;
}
