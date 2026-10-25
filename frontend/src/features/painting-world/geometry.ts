/** Fit the whole displaced artwork before allowing deliberate detail zoom. */
export function fitArtworkCamera(input: {
  planeHeight:number; planeWidth:number; fov:number; amplitude:number;
  width:number; height:number; entryScale:number;
}) {
  const viewportAspect=Math.max(input.width,1)/Math.max(input.height,1);
  const fullHeight=Math.max(input.planeHeight,input.planeWidth/viewportAspect);
  const rest=fullHeight/(2*Math.tan(input.fov*Math.PI/360))*1.08+input.amplitude;
  return {rest,start:rest*Math.max(input.entryScale,1.2),near:Math.max(input.amplitude+.35,rest*.62)};
}

/** Texture UV has its origin at bottom-left; artwork coordinates use top-left. */
export function pickHotspotFromUv(spots:Array<{id:string;x:number;y:number}>, u:number, v:number):string|null {
  let nearest:{id:string;distance:number}|null=null;
  for (const spot of spots) {
    const distance=Math.hypot(u-spot.x,(1-v)-spot.y);
    if (distance<.085 && (!nearest || distance<nearest.distance)) nearest={id:spot.id,distance};
  }
  return nearest?.id??null;
}
