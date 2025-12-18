#version 120

// Standard Panda3D inputs
attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec2 p3d_MultiTexCoord0;

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat3 p3d_NormalMatrix;

varying vec3 v_normal;
varying vec3 v_viewDir;
varying vec2 v_uv;

void main() {
    // Transform vertex position
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

    // Calculate view-space normal
    v_normal = normalize(p3d_NormalMatrix * p3d_Normal);

    // Calculate view direction (vector from vertex to camera in view space)
    vec4 viewPos = p3d_ModelViewMatrix * p3d_Vertex;
    v_viewDir = normalize(-viewPos.xyz);

    v_uv = p3d_MultiTexCoord0;
}