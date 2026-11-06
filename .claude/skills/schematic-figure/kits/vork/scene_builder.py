# .claude/skills/schematic-figure/kits/vork/scene_builder.py
"""
vork 3D Scene Builder & SVG Anchor Compositor for schematic-figure.
"""

import base64
import colorsys
import json
import math
import subprocess
from pathlib import Path
import numpy as np


def _quat_from_y_to_vec(vec):
    """Returns [x, y, z, w] quaternion rotating canonical +Y (0, 1, 0) to unit `vec`."""
    v = np.asarray(vec, dtype=float)
    v /= np.linalg.norm(v) + 1e-12
    y_axis = np.array([0.0, 1.0, 0.0])
    dot = float(np.dot(y_axis, v))

    if dot < -0.999999:
        return [1.0, 0.0, 0.0, 0.0]

    cross = np.cross(y_axis, v)
    w = 1.0 + dot
    q = np.array([cross[0], cross[1], cross[2], w], dtype=float)
    q /= np.linalg.norm(q)
    return [round(float(c), 5) for c in q]


def _spin_to_rgb(sx, sz_up, sy_inplane, scheme="hsl"):
    """Matches spin_vector_lattice.slang color_from_spin()."""
    sz = max(-1.0, min(1.0, float(sz_up)))
    if scheme == "hsl":
        phi = math.atan2(sy_inplane, sx)
        hue = (phi / (2.0 * math.pi)) % 1.0
        lightness = 0.08 + 0.86 * (0.5 * (sz + 1.0))
        r, g, b = colorsys.hls_to_rgb(hue, lightness, 0.90)
        return [round(r, 4), round(g, 4), round(b, 4)]
    else:
        if sz < 0:
            t = -sz
            c = (1 - t) * np.array([0.92, 0.92, 0.90]) + t * np.array([0.08, 0.28, 0.68])
        else:
            t = sz
            c = (1 - t) * np.array([0.92, 0.92, 0.90]) + t * np.array([0.78, 0.12, 0.16])
        return [round(float(x), 4) for x in c]


class VorkSchematicScene:
    def __init__(self, width=1600, height=1200, fov_deg=35.0):
        self.width = width
        self.height = height
        self.fov_deg = fov_deg
        self.nodes = []
        self.anchors_3d = {}  # name -> [x, y, z]
        self.camera = {
            "type": "camera",
            "translation": [4.0, 3.0, 6.0],
            "target": [0.0, 0.0, 0.0],
            "fov": fov_deg,
        }

    def set_camera(self, translation, target, fov_deg=35.0):
        self.fov_deg = fov_deg
        self.camera = {
            "type": "camera",
            "translation": [float(c) for c in translation],
            "target": [float(c) for c in target],
            "fov": float(fov_deg),
        }

    def add_node(self, node_dict, anchor_name=None, anchor_offset=(0.0, 0.0, 0.0)):
        self.nodes.append(node_dict)
        if anchor_name and "translation" in node_dict:
            t = node_dict["translation"]
            self.anchors_3d[anchor_name] = [
                float(t[0] + anchor_offset[0]),
                float(t[1] + anchor_offset[1]),
                float(t[2] + anchor_offset[2]),
            ]

    def add_studio_lights(self):
        self.nodes.extend([
            {
                "type": "light",
                "shape": "rectangle",
                "translation": [-4.0, 6.0, 5.0],
                "target": [0.0, 0.0, 0.0],
                "energy": 800,
                "size": 4,
                "color": [1.0, 0.96, 0.9],
            },
            {
                "type": "light",
                "shape": "rectangle",
                "translation": [5.0, 3.0, -3.0],
                "target": [0.0, 0.0, 0.0],
                "energy": 350,
                "size": 5,
                "color": [0.85, 0.92, 1.0],
            },
        ])

    def add_wave_or_potential_plane(
        self,
        mode="wave_interference",
        sources=None,
        size=(8.0, 8.0),
        y_level=0.0,
        contour_spacing=0.25,
        normal_scale=0.35,
        program_path="kits/vork/programs/wave_potential_field.slang",
    ):
        mode_map = {"wave_interference": 0, "potential_well": 1, "optical_lattice": 2}
        sources = sources or []

        formatted_sources = []
        for src in sources[:8]:
            pos = [float(c) for c in src.get("pos", [0.0, y_level, 0.0])]
            if "label" in src:
                self.anchors_3d[src["label"]] = pos
            formatted_sources.append({
                "position": pos,
                "amplitude": float(src.get("amp", 1.0)),
                "wavelength": float(src.get("wavelength", 0.75)),
                "phase": float(src.get("phase", 0.0)),
            })

        self.nodes.append({
            "type": "mesh",
            "translation": [0.0, float(y_level), 0.0],
            "geometry": {"std": "grid", "size": [float(size[0]), float(size[1])]},
            "materials": [{
                "program": program_path,
                "inputs": {
                    "mode": mode_map[mode],
                    "num_sources": len(formatted_sources),
                    "time": 0.0,
                    "damping": 0.12,
                    "contour_spacing": float(contour_spacing),
                    "contour_strength": 0.45,
                    "normal_scale": float(normal_scale),
                    "envelope_radius": float(min(size) * 0.45),
                    "sources": formatted_sources,
                },
            }],
        })

    def add_spin_lattice(
        self,
        nx=19,
        nz=19,
        spacing=0.42,
        y_level=0.25,
        skyrmion_radius=2.2,
        vorticity=1.0,
        helicity=0.0,
        polarity=-1.0,
        color_scheme="hsl",
        arrow_scale=0.34,
        add_substrate=True,
    ):
        half_x = 0.5 * (nx - 1) * spacing
        half_z = 0.5 * (nz - 1) * spacing

        if add_substrate:
            self.nodes.append({
                "type": "mesh",
                "translation": [0.0, round(y_level - 0.28, 3), 0.0],
                "geometry": {"std": "grid", "size": [round(2 * half_x + 1.2, 3), round(2 * half_z + 1.2, 3)]},
                "materials": [{
                    "inputs": {
                        "base_color": [0.16, 0.18, 0.22],
                        "specular_roughness": 0.45,
                    }
                }],
            })

        for ix in range(nx):
            for iz in range(nz):
                x = -half_x + ix * spacing
                z = -half_z + iz * spacing
                rho = math.hypot(x, z)
                phi = math.atan2(z, x)

                theta = math.pi * math.exp(-rho / max(skyrmion_radius, 0.1))
                angle = vorticity * phi + helicity

                sx = math.sin(theta) * math.cos(angle)
                sy_inplane = math.sin(theta) * math.sin(angle)
                # polarity < 0 keeps cos(theta): core down (Sz = -1), background up.
                sz_up = math.cos(theta) if polarity < 0 else -math.cos(theta)

                quat = _quat_from_y_to_vec([sx, sz_up, sy_inplane])
                rgb = _spin_to_rgb(sx, sz_up, sy_inplane, scheme=color_scheme)

                self.nodes.append({
                    "type": "mesh",
                    "translation": [round(x, 3), round(y_level, 3), round(z, 3)],
                    "rotation": quat,
                    "scale": [round(arrow_scale * 0.35, 4), round(arrow_scale, 4), round(arrow_scale * 0.35, 4)],
                    "geometry": {"std": "cone", "radius": 1.0, "height": 2.0},
                    "materials": [{
                        "inputs": {
                            "base_color": rgb,
                            "specular_roughness": 0.25,
                        }
                    }],
                })

        self.anchors_3d["skyrmion_core"] = [0.0, round(y_level + arrow_scale, 3), 0.0]
        r_inplane = skyrmion_radius * math.log(2.0)
        self.anchors_3d["domain_wall_ring"] = [round(r_inplane, 3), round(y_level, 3), 0.0]
        self.anchors_3d["ferromagnetic_bg"] = [
            round(half_x, 3),
            round(y_level + arrow_scale, 3),
            round(-half_z, 3),
        ]

    def project_anchors_to_svg(self, svg_width, svg_height):
        """Projects 3D world anchors to 2D SVG coordinates (origin top-left)."""
        cam_pos = np.array(self.camera["translation"], dtype=float)
        cam_target = np.array(self.camera["target"], dtype=float)
        up = np.array([0.0, 1.0, 0.0])

        forward = cam_target - cam_pos
        forward /= np.linalg.norm(forward)
        right = np.cross(forward, up)
        right /= np.linalg.norm(right)
        true_up = np.cross(right, forward)

        aspect = float(self.width) / float(self.height)
        scale = math.tan(math.radians(self.fov_deg * 0.5))

        projected = {}
        for name, pt in self.anchors_3d.items():
            rel = np.array(pt, dtype=float) - cam_pos
            x_cam = float(np.dot(rel, right))
            y_cam = float(np.dot(rel, true_up))
            z_cam = float(np.dot(rel, forward))

            if z_cam <= 0.0:
                continue

            ndc_x = x_cam / (z_cam * scale * aspect)
            ndc_y = y_cam / (z_cam * scale)

            svg_x = (ndc_x + 1.0) * 0.5 * svg_width
            svg_y = (1.0 - ndc_y) * 0.5 * svg_height
            projected[name] = (round(svg_x, 1), round(svg_y, 1))

        return projected

    def write_json(self, json_path):
        scene_data = {
            "version": 2,
            "nodes": self.nodes + [self.camera],
            "render": {"resolution": [self.width, self.height]},
        }
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(scene_data, indent=2))

    def render(self, json_path, out_png, profile="std/previs", extra_args=None):
        self.write_json(json_path)
        Path(out_png).parent.mkdir(parents=True, exist_ok=True)
        cmd = ["vork", "render", str(json_path), "--profile", profile, "--out", str(out_png)]
        if extra_args:
            cmd.extend(extra_args)
        subprocess.run(cmd, check=True)

    def export_composite_svg(self, render_png_path, out_svg_path, svg_width=600, svg_height=450, callouts=None):
        """
        Embeds the rendered vork PNG into a publication SVG with crisp vector callout lines,
        text labels, and an optional Sz/phi or CoolWarm legend.
        `callouts` format: [{"anchor": "skyrmion_core", "label": "Core (Sz = -1)", "dx": -70, "dy": -55}]
        """
        anchors_2d = self.project_anchors_to_svg(svg_width, svg_height)
        png_bytes = Path(render_png_path).read_bytes()
        b64_png = base64.b64encode(png_bytes).decode("ascii")

        callouts = callouts or []
        overlay_elements = []

        for item in callouts:
            anchor_key = item["anchor"]
            if anchor_key not in anchors_2d:
                continue
            ax, ay = anchors_2d[anchor_key]
            lx = round(ax + item.get("dx", 40), 1)
            ly = round(ay + item.get("dy", -40), 1)
            text_anchor = "end" if item.get("dx", 40) < 0 else "start"
            label_x = lx - 4 if text_anchor == "end" else lx + 4

            overlay_elements.append(
                f'  <line x1="{lx}" y1="{ly}" x2="{ax}" y2="{ay}" '
                f'stroke="#111827" stroke-width="1.25" marker-end="url(#arrow)" />'
            )
            overlay_elements.append(
                f'  <circle cx="{ax}" cy="{ay}" r="2.2" fill="#111827" />'
            )
            overlay_elements.append(
                f'  <text x="{label_x}" y="{ly + 3}" text-anchor="{text_anchor}" '
                f'font-family="Latin Modern Roman, Arial, sans-serif" font-size="11" '
                f'fill="#111827">{item["label"]}</text>'
            )

        overlays_str = "\n".join(overlay_elements)
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#111827" />
    </marker>
  </defs>
  <image href="data:image/png;base64,{b64_png}" x="0" y="0" width="{svg_width}" height="{svg_height}" preserveAspectRatio="xMidYMid meet" />
{overlays_str}
</svg>
"""
        Path(out_svg_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_svg_path).write_text(svg_content)
        return anchors_2d
