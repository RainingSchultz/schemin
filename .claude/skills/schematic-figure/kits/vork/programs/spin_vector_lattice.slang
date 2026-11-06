// kits/vork/programs/spin_vector_lattice.slang
// Reusable 3D Vector Field & Magnetic Spin Lattice Shader for schematic-figure

struct SpinDefect {
    float3 center;       // Defect core position (x0, y0, z0)
    float  radius;       // Skyrmion/vortex radius R_sk
    float  vorticity;    // Winding number m (+1 = skyrmion, -1 = antiskyrmion)
    float  helicity;     // gamma (0 = Neel hedgehog, pi/2 = Bloch vortex)
    float  polarity;     // Core polarity p (-1 = core down in +z background, +1 = core up)
};

struct SpinLatticeParams {
    int    mode;            // 0 = Topological Skyrmion Lattice, 1 = Spin Spiral / Domain Wall, 2 = 3D Magnetic Dipole Field
    int    color_scheme;    // 0 = Condensed-Matter HSL (Sz -> Lightness, phi -> Hue), 1 = Diverging Sz (Blue-White-Red)
    int    num_defects;     // Up to 8 topological defects / dipoles
    float3 background_spin; // Asymptotic background spin
    float  q_pitch;         // Wavevector q for spin spirals (Mode 1)
    float  cone_angle;      // Conical tilt angle theta (Mode 1)
    SpinDefect defects[8];
};

static const float PI     = 3.14159265359;
static const float TWO_PI = 6.28318530718;

// 1. Evaluate Normalized 3D Spin Vector S(r) = (Sx, Sz_outofplane_Y, Sy_inplane_Z)
float3 evaluate_spin_vector(float3 world_pos, SpinLatticeParams params) {
    float2 r_plane = world_pos.xz;

    if (params.mode == 0) {
        float2 omega_sum = float2(0.0, 0.0);

        [ForceUnroll]
        for (int i = 0; i < 8; ++i) {
            if (i >= params.num_defects) break;
            SpinDefect d = params.defects[i];

            float2 rel = r_plane - d.center.xz;
            float  rho = max(length(rel), 1e-5);
            float  phi = atan2(rel.y, rel.x);

            float profile = PI * exp(-rho / max(d.radius, 0.1));
            float tan_half = tan(0.5 * clamp(profile, 0.0, PI - 1e-3));

            float angle = d.vorticity * phi + d.helicity;
            omega_sum += tan_half * float2(cos(angle), sin(angle));
        }

        float w2 = dot(omega_sum, omega_sum);
        float sx = 2.0 * omega_sum.x / (1.0 + w2);
        float sy = 2.0 * omega_sum.y / (1.0 + w2);
        float sz = (1.0 - w2) / (1.0 + w2);

        // The stereographic profile is already core-down (Sz = -1). Flip only for positive polarity.
        float pol = (params.num_defects > 0) ? params.defects[0].polarity : -1.0;
        if (pol > 0.0) {
            sz = -sz;
        }
        return normalize(float3(sx, sz, sy));
    }
    else if (params.mode == 1) {
        float phase = params.q_pitch * r_plane.x;
        float helicity = (params.num_defects > 0) ? params.defects[0].helicity : 0.0;
        float sx = sin(phase) * cos(helicity);
        float sy = sin(phase) * sin(helicity);
        float sz = cos(phase);
        return normalize(float3(sx, sz, sy));
    }
    else {
        float3 B = float3(0.0, 0.0, 0.0);
        [ForceUnroll]
        for (int i = 0; i < 8; ++i) {
            if (i >= params.num_defects) break;
            SpinDefect d = params.defects[i];
            float3 r_vec = world_pos - d.center;
            float  r2 = max(dot(r_vec, r_vec), 0.15);
            float  r  = sqrt(r2);
            float3 r_hat = r_vec / r;

            float3 m_vec = float3(0.0, d.polarity * d.radius, 0.0);
            B += (3.0 * dot(m_vec, r_hat) * r_hat - m_vec) / (r2 * r);
        }
        return normalize(B + 1e-5 * float3(0.0, 1.0, 0.0));
    }
}

// 2. Condensed-Matter Spherical Colormap: (Sx, Sz_up, Sy) -> RGB
float3 hsl_to_rgb(float h, float s, float l) {
    float3 rgb = clamp(abs(fmod(h * 6.0 + float3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
    rgb = rgb * rgb * (3.0 - 2.0 * rgb);
    float c = (1.0 - abs(2.0 * l - 1.0)) * s;
    return (rgb - 0.5) * c + l;
}

float3 color_from_spin(float3 s_world, int scheme, float local_tip_mask) {
    float sx = s_world.x;
    float sz = clamp(s_world.y, -1.0, 1.0);
    float sy = s_world.z;

    float3 base_col;
    if (scheme == 0) {
        float phi = atan2(sy, sx);
        float hue = frac(phi / TWO_PI + 1.0);
        float lightness = lerp(0.08, 0.94, 0.5 * (sz + 1.0));
        base_col = hsl_to_rgb(hue, 0.90, lightness);
    } else {
        float3 down_col = float3(0.08, 0.28, 0.68);
        float3 zero_col = float3(0.92, 0.92, 0.90);
        float3 up_col   = float3(0.78, 0.12, 0.16);
        base_col = (sz < 0.0)
            ? lerp(zero_col, down_col, -sz)
            : lerp(zero_col, up_col, sz);
    }
    return base_col * lerp(0.82, 1.05, local_tip_mask);
}

// 3. Orthonormal Basis Builder (Aligns a +Y Canonical Arrow to Spin Vector S)
float3x3 align_y_to_vector(float3 s) {
    float3 up = normalize(s);
    float3 helper = (abs(up.y) < 0.999) ? float3(0.0, 1.0, 0.0) : float3(1.0, 0.0, 0.0);
    float3 right = normalize(cross(helper, up));
    float3 fwd   = cross(up, right);
    return float3x3(right, up, fwd);
}
