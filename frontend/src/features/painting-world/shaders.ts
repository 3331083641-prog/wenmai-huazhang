/**
 * 画境着色器：深度位移网格 + 三处克制的地方性动态。
 *
 * 设计原则（对应验收里的「不能破坏原作艺术风格」）：
 *   1. 不做光照计算。青绿山水是设色画，加光源立刻变成写实游戏场景。
 *   2. 动态都作用在「本来就该动的地方」：云气、水纹、近景枝叶，
 *      并且振幅压到只在仔细观察时才看得出来。
 *   3. 远处向纸色靠（空气透视），近处保持原色饱和度，这样空间感来自
 *      色彩关系而不是明暗，仍是「画」的逻辑。
 */

export const paintingVertexShader = /* glsl */ `
uniform sampler2D uDepth;
uniform sampler2D uMasks;
uniform float uAmplitude;
uniform float uSway;
uniform float uTime;

varying vec2 vUv;
varying float vDepth;

/** RG 两通道还原 16 位深度（PNG 只有 8 位/channel，单通道会有明显台阶）。 */
float decodeDepth(vec2 uv) {
  vec2 rg = texture2D(uDepth, uv).rg;
  return (rg.x * 255.0 * 256.0 + rg.y * 255.0) / 65535.0;
}

void main() {
  vUv = uv;
  float d = decodeDepth(uv);
  vDepth = d;

  vec3 pos = position;
  // 深度越大越靠近观众：整张画被「撑」成一个有厚度的浅浮雕
  pos.z += d * uAmplitude;

  // 近景枝叶轻摆：只作用在 masks.B 标记的区域，且振幅极小
  // 用 smoothstep 压掉羽化边缘的弱值：否则整张网格都在被推、推得还都很轻微，
  // 观感是「整幅画在抖」，而不是「近处枝叶在动」。
  float foliage = smoothstep(0.25, 0.78, texture2D(uMasks, uv).b);
  float phase = uTime * 1.35 + uv.x * 11.0 + uv.y * 6.5;
  pos.z += sin(phase) * 0.0035 * foliage * uSway;
  pos.x += cos(phase * 0.8) * 0.0018 * foliage * uSway;

  vec4 world = modelMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

export const paintingFragmentShader = /* glsl */ `
uniform sampler2D uArt;
uniform sampler2D uMasks;
uniform float uTime;
uniform float uHaze;
uniform float uMist;
uniform float uRipple;
uniform vec3 uPaper;

varying vec2 vUv;
varying float vDepth;

void main() {
  vec2 uv = clamp(vUv, 0.0, 1.0);

  float water = texture2D(uMasks, uv).r;
  float mistMask = texture2D(uMasks, uv).g;

  // 水纹：两组不同频率的正弦叠加，轻微扭曲采样坐标
  float ripple =
      sin(uv.y * 88.0 + uTime * 0.85) * 0.6
    + sin(uv.x * 47.0 - uTime * 0.62) * 0.4;
  vec2 warp = vec2(
    ripple * 0.0026,
    sin(uv.x * 61.0 + uTime * 0.5) * 0.0018
  ) * water * uRipple;
  vec3 col = texture2D(uArt, uv + warp).rgb;

  // 空气透视：越远越向纸色靠
  col = mix(col, uPaper, (1.0 - vDepth) * uHaze);

  // 云雾流动：遮罩本身缓慢偏移 + 低频亮度起伏
  // 只做「亮度呼吸」时，平滑的遮罩整体明暗变化，看不出云在走；
  // 叠加一层随 uv 变化的高频细节，偏移才读作云气在推、在卷。
  float drift = sin(uTime * 0.075 + uv.y * 4.2) * 0.026
              + sin(uTime * 0.041 + uv.x * 2.1) * 0.015;
  float mist = texture2D(uMasks, clamp(uv + vec2(drift, drift * 0.35), 0.0, 1.0)).g;
  float billow = 0.45 + 0.55 * sin(uv.x * 17.0 + uTime * 0.55 + uv.y * 5.0);
  float breath = 0.55 + 0.45 * sin(uTime * 0.34 + uv.x * 5.5 + uv.y * 2.0);
  // 遮罩的羽化边缘（0.05~0.25）遍布大半张画，直接乘上去会让整幅画一起明暗呼吸，
  // 读起来像「一张会浮动的照片」。这里先用 smoothstep 把弱值压掉，只让真正的云气参与。
  float mistCore = smoothstep(0.22, 0.72, mist);
  col = mix(col, uPaper * 1.03, mistCore * billow * breath * uMist);

  // 水光：只在波纹的波峰处给一点提亮，避免整体发灰
  col += water * vec3(0.050, 0.068, 0.066) * smoothstep(0.35, 1.0, ripple) * uRipple;

  // 纸纹：极轻的噪点，压掉数字贴图的「平」
  float grain = fract(sin(dot(uv * vec2(1024.0, 683.0), vec2(12.9898, 78.233))) * 43758.5453);
  col *= 0.988 + grain * 0.024;

  // 边缘轻微压暗，把视线收在画面内
  vec2 c = uv - 0.5;
  float vig = smoothstep(0.86, 0.34, length(c * vec2(1.0, 1.12)));
  col *= mix(0.90, 1.0, vig);

  gl_FragColor = vec4(col, 1.0);
}
`;