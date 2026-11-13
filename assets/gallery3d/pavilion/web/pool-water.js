import * as THREE from 'three';

export const pools=[
  {x:20,z:25,length:22,surface:-.55,bed:-3.05},
  {x:9,z:-33,length:12,surface:-.30,bed:-2.45}
];
export function poolAt(x,z) {
  return pools.find(p=>Math.abs(x)<p.x-.008 && Math.abs(z-p.z)<p.length/2-.008);
}

export function makePools(scene,renderer,normalMap) {
  // A mirrored scene view provides moving reflections of the actual pavilions.
  const targets=pools.map(()=>new THREE.WebGLRenderTarget(480,320,{type:THREE.HalfFloatType}));
  const mirror=new THREE.PerspectiveCamera(), direction=new THREE.Vector3();
  const clip=new THREE.Plane(new THREE.Vector3(0,1,0),0);
  const surfaceGroup=new THREE.Group();
  const clock={value:0},wake={value:new THREE.Vector3(1000,1000,-100)};
  const shaders=[];
  for(const pool of pools) {
    const geometry=new THREE.PlaneGeometry(pool.x*2-.016,pool.length-.016,Math.ceil(pool.x*2/.38),Math.ceil(pool.length/.38));
    geometry.rotateX(-Math.PI/2);
    const uniforms={
      clock,wake, normalTex:{value:normalMap},reflectTex:{value:targets[shaders.length].texture},
      mirrorVP:{value:new THREE.Matrix4()}, poolSize:{value:new THREE.Vector2(pool.x,pool.length/2)},
      deep:{value:new THREE.Color('#36756f')},sky:{value:new THREE.Color('#b0d4da')}
    };
    const mat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide,uniforms,
      vertexShader:`
        uniform float clock; uniform vec3 wake; uniform mat4 mirrorVP;
        varying vec3 point; varying vec2 localP; varying vec4 projected;
        void main(){
          localP=position.xz; point=(modelMatrix*vec4(position,1.)).xyz;
          float r=distance(point.xz,wake.xy);
          float age=clock-wake.z;
          point.y+=.013*sin(dot(point.xz,vec2(1.7,.6))+clock*1.25)
                   +.009*sin(dot(point.xz,vec2(-.9,2.1))-clock*.84)
                   +.025*sin(11.*r-8.*age)*exp(-1.4*abs(r-1.4*age)-.6*age);
          projected=mirrorVP*vec4(point,1.);
          gl_Position=projectionMatrix*viewMatrix*vec4(point,1.);
        }`,
      fragmentShader:`
        uniform sampler2D normalTex,reflectTex; uniform vec2 poolSize;
        uniform float clock; uniform vec3 deep,sky;
        varying vec3 point; varying vec2 localP; varying vec4 projected;
        void main(){
          if(distance(abs(localP),poolSize)<.181) discard;
          vec2 p=point.xz;
          vec2 a=texture2D(normalTex,p*.17+clock*vec2(.009,.012)).rg-.5;
          vec2 b=texture2D(normalTex,p.yx*.29-clock*vec2(.014,.004)).gr-.5;
          vec3 n=normalize(cross(dFdx(point),dFdy(point)));
          if(n.y<0.) n=-n;
          n=normalize(n+vec3((a.x+b.x)*.44,0.,(a.y+b.y)*.44));
          vec3 v=normalize(cameraPosition-point);
          float f=.025+.85*pow(1.-abs(dot(n,v)),3.);
          vec2 uv=projected.xy/projected.w*.5+.5+(a+b)*.028;
          vec3 refl=texture2D(reflectTex,clamp(uv,.002,.998)).rgb;
          if(any(lessThan(uv,vec2(0.))) || any(greaterThan(uv,vec2(1.)))) refl=sky;
          float glint=pow(max(dot(reflect(-normalize(vec3(-.45,.85,.29)),n),v),0.),110.);
          vec3 col=mix(deep,refl,f)+vec3(.8,.69,.49)*glint;
          gl_FragColor=vec4(col,gl_FrontFacing ? .35+.58*f : .28);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`});
    const mesh=new THREE.Mesh(geometry,mat);
    mesh.position.set(0,pool.surface,pool.z);
    mesh.renderOrder=2;
    surfaceGroup.add(mesh);
    shaders.push(uniforms);
  }
  scene.add(surfaceGroup);
  let lastReflection=-2,lastWake=-2,lastX=0,lastZ=0,reflectionIndex=0;
  const fog=new THREE.FogExp2('#327775',.12);
  function tick(t,camera,swimming) {
    clock.value=t;
    const {x,y,z}=camera.position, p=poolAt(x,z);
    scene.fog=swimming && p && y<p.surface-.035 ? fog : null;
    if(swimming && p && y>p.surface-.24 && t-lastWake>.48 && Math.hypot(x-lastX,z-lastZ)>.15) {
      wake.value.set(x,z,t);lastWake=t;lastX=x;lastZ=z;
    }
    if(t-lastReflection<.22 || scene.fog) return;
    lastReflection=t;
    // Alternate the two render targets. Each pool reflects at its own elevation.
    const index=reflectionIndex++%pools.length;
    const height=pools[index].surface;
    camera.updateMatrixWorld();
    camera.getWorldDirection(direction);
    mirror.copy(camera,false);
    mirror.position.y=2*height-y;
    direction.y*=-1;
    mirror.up.copy(camera.up).reflect(new THREE.Vector3(0,1,0)).negate();
    mirror.lookAt(direction.add(mirror.position));
    mirror.updateMatrixWorld();
    shaders[index].mirrorVP.value.multiplyMatrices(mirror.projectionMatrix,mirror.matrixWorldInverse);
    const oldTarget=renderer.getRenderTarget(),oldPlanes=renderer.clippingPlanes;
    const updateShadows=renderer.shadowMap.needsUpdate;
    renderer.shadowMap.needsUpdate=false;
    clip.constant=-height;
    renderer.clippingPlanes=[clip];
    surfaceGroup.visible=false;
    renderer.setRenderTarget(targets[index]);
    renderer.render(scene,mirror);
    renderer.setRenderTarget(oldTarget);
    renderer.clippingPlanes=oldPlanes;
    renderer.shadowMap.needsUpdate=updateShadows;
    surfaceGroup.visible=true;
  }
  return {tick};
}
