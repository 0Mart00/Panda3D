#version 120

// Panda3D beépített uniformok
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;

attribute vec4 p3d_Vertex;
attribute vec2 p3d_MultiTexCoord0;

varying vec2 texcoord;
varying float distToCamera;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord = p3d_MultiTexCoord0;

    // Kiszámoljuk a vertex távolságát a kamerától (view space-ben)
    vec4 viewPos = p3d_ModelViewMatrix * p3d_Vertex;
    distToCamera = length(viewPos.xyz);
}