#version 120

uniform sampler2D p3d_Texture0;
uniform float fogDensity;
uniform float fogEnd; // Opcionális: manuális levágáshoz

varying vec2 texcoord;
varying float distToCamera;

void main() {
    vec4 texColor = texture2D(p3d_Texture0, texcoord);
    
    // Köd szín (pl. világosszürke)
    vec3 fogColor = vec3(0.5, 0.6, 0.7);

    // Számítás: Minél messzebb van, annál több a köd
    // 1. Lineáris köd logika:
    // float fogFactor = (fogEnd - distToCamera) / fogEnd;
    
    // 2. Exponenciális köd logika (szebb, természetesebb):
    float fogFactor = 1.0 / exp(pow(distToCamera * fogDensity, 2.0));

    // A fogFactor 0 és 1 közé szorítása
    fogFactor = clamp(fogFactor, 0.0, 1.0);

    // Keverés: Ha fogFactor 1 -> textúra, ha 0 -> köd szín
    vec3 finalColor = mix(fogColor, texColor.rgb, fogFactor);

    gl_FragColor = vec4(finalColor, texColor.a);
}