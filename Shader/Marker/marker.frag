#version 120

varying vec3 v_normal;
varying vec3 v_viewDir;
varying vec2 v_uv;

uniform float u_colorSteps;    // e.g., 4.0
uniform float u_noiseStrength; // e.g., 0.15
uniform float u_outlineWidth;  // e.g., 0.4
uniform vec4 u_baseColor;      // Object color

// Simple pseudo-random hash based on UV coordinates
float rand(vec2 co) {
    return fract(sin(dot(co.xy, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    // 1. Normalize vectors
    vec3 N = normalize(v_normal);
    vec3 V = normalize(v_viewDir);
    
    // Fixed directional light (overhead-right)
    vec3 L = normalize(vec3(0.5, 0.8, 0.5));

    // 2. Generate Paper/Ink Noise
    float noise = rand(v_uv * 20.0) * u_noiseStrength;
    
    // 3. Lambert Diffuse Lighting
    float NdotL = max(dot(N, L), 0.0);
    
    // 4. Quantize Lighting (Cel-Shading steps)
    // We add noise BEFORE quantization to make the ink edges uneven
    float intensity = NdotL + (noise - (u_noiseStrength * 0.5));
    float stepped = floor(intensity * u_colorSteps) / u_colorSteps;
    
    // Clamp limits to avoid absolute black in shadows (paper reflection)
    stepped = clamp(stepped, 0.2, 1.0);

    // 5. Ink Edge / Outline Logic (Fresnel based)
    // Calculates how perpendicular the surface is to the camera
    float NdotV = dot(N, V);
    float edgeFactor = smoothstep(0.0, u_outlineWidth, NdotV);
    
    // 6. Composition
    vec3 finalColor = u_baseColor.rgb * stepped;
    
    // Apply marker bleed/outline (darkens edges)
    // Using pow to make the edge sharper, resembling a stroke
    finalColor *= pow(edgeFactor, 0.5); 

    gl_FragColor = vec4(finalColor, 1.0);
}