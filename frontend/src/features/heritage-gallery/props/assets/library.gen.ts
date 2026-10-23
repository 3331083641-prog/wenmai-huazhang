// @ts-nocheck
/**
 * 器物资产库（由 Gemini 的 5.html 精确移植）
 *
 * 来源：C:\\Users\\WPY11\\Desktop\\5.html 的 MAT / 纹理生成器 / box / cyl /
 * addFlushSpandrel / BUILDERS。只保留用户白名单里的 14 件，另外五件
 * （DIY_A06 / A10 / B05 / C03 / D05）的构建代码根本没有抽进来。
 *
 * 为什么不用原 HTML 的 GLB 导出：那个导出器把手写几何展开成大量独立节点，
 * 且不保证 CanvasTexture / 透明 / 父子关系完整。这里直接把原始构建函数接进
 * Three.js 运行时构建，纹理由 canvas 现场生成，节点名与父子层级与原始一致，
 * 交互控制器按节点名找零件。
 */

import * as THREE from 'three';

      function makeWoodTex(bg, line) {
        const c = document.createElement('canvas'); c.width = 512; c.height = 512;
        const ctx = c.getContext('2d');
        ctx.fillStyle = bg; ctx.fillRect(0, 0, 512, 512);
        for (let i = 0; i < 450; i++) {
          const y = Math.random() * 512;
          ctx.strokeStyle = line;
          ctx.globalAlpha = 0.10 + Math.random() * 0.16;
          ctx.lineWidth = 1 + Math.random() * 2;
          ctx.beginPath(); ctx.moveTo(0, y);
          ctx.bezierCurveTo(170, y + Math.sin(y * 0.05) * 10, 340, y - Math.cos(y * 0.05) * 10, 512, y);
          ctx.stroke();
        }
        const t = new THREE.CanvasTexture(c);
        t.wrapS = t.wrapT = THREE.RepeatWrapping;
        return t;
      }

      function makeRuimaoTex() {
        const c = document.createElement('canvas'); c.width = 512; c.height = 512;
        const ctx = c.getContext('2d');
        ctx.fillStyle = '#F4EAD5'; ctx.fillRect(0, 0, 512, 512);
        ctx.fillStyle = '#C42B22'; ctx.fillRect(28, 28, 456, 456);
        ctx.strokeStyle = '#231815'; ctx.lineWidth = 8; ctx.strokeRect(28, 28, 456, 456);
        for (let x = 56; x <= 456; x += 64) {
          ctx.fillStyle = '#1E7A65';
          ctx.beginPath(); ctx.arc(x, 476, 36, Math.PI, 0); ctx.fill(); ctx.stroke();
        }
        ctx.fillStyle = '#E8B042'; ctx.fillRect(126, 46, 260, 54); ctx.strokeRect(126, 46, 260, 54);
        ctx.fillStyle = '#231815'; ctx.font = 'bold 34px serif';
        ctx.textAlign = 'center'; ctx.fillText('瑞 猫 迎 春', 256, 85);
        ctx.fillStyle = '#D99538';
        ctx.beginPath(); ctx.ellipse(250, 305, 82, 56, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.beginPath(); ctx.arc(195, 220, 48, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.fillStyle = '#1B7A62';
        ctx.beginPath(); ctx.arc(178, 215, 9, 0, Math.PI * 2); ctx.arc(212, 215, 9, 0, Math.PI * 2); ctx.fill();
        return new THREE.CanvasTexture(c);
      }

      function makeBianSilkTex() {
        const c = document.createElement('canvas'); c.width = 512; c.height = 512;
        const ctx = c.getContext('2d');
        ctx.fillStyle = '#EFE5D0'; ctx.fillRect(0, 0, 512, 512);
        ctx.fillStyle = '#F7F1E3';
        ctx.beginPath(); ctx.arc(256, 256, 215, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = '#C89B4E'; ctx.lineWidth = 6; ctx.stroke();
        ctx.strokeStyle = '#52341E'; ctx.lineWidth = 7;
        ctx.beginPath(); ctx.moveTo(110, 400); ctx.quadraticCurveTo(230, 290, 340, 190); ctx.stroke();
        [[190, 310, -0.4], [280, 280, 0.5], [220, 210, -0.6], [330, 240, 0.4]].forEach(([lx, ly, rot]) => {
          ctx.fillStyle = '#287A62';
          ctx.beginPath(); ctx.ellipse(lx, ly, 38, 16, rot, 0, Math.PI * 2); ctx.fill();
        });
        for (let r = 68; r >= 22; r -= 15) {
          ctx.fillStyle = r > 45 ? '#C42E24' : (r > 30 ? '#DE5D4E' : '#F09C8C');
          for (let a = 0; a < Math.PI * 2; a += Math.PI / 5) {
            ctx.beginPath(); ctx.arc(256 + Math.cos(a) * (r * 0.55), 265 + Math.sin(a) * (r * 0.55), r * 0.48, 0, Math.PI * 2); ctx.fill();
          }
        }
        ctx.fillStyle = '#E8B448'; ctx.beginPath(); ctx.arc(256, 265, 16, 0, Math.PI * 2); ctx.fill();
        return new THREE.CanvasTexture(c);
      }

      function makeSongLandscapeTex(shift = 0) {
        const c = document.createElement('canvas'); c.width = 512; c.height = 512;
        const ctx = c.getContext('2d');
        const g = ctx.createLinearGradient(0, 0, 0, 512);
        g.addColorStop(0, '#DFCEAC'); g.addColorStop(0.55, '#ECE2CA'); g.addColorStop(1, '#CBB894');
        ctx.fillStyle = g; ctx.fillRect(0, 0, 512, 512);
        [[230, 60, 0.008, 'rgba(36,82,114,0.48)'], [310, 82, 0.011, '#1A4F75'], [395, 55, 0.015, '#287862']].forEach(([yb, amp, f, col]) => {
          ctx.beginPath(); ctx.moveTo(0, 512);
          for (let x = 0; x <= 512; x += 6) {
            ctx.lineTo(x, yb - Math.sin(x * f + shift) * amp - Math.cos(x * f * 2.2 + shift) * amp * 0.35);
          }
          ctx.lineTo(512, 512); ctx.closePath();
          ctx.fillStyle = col; ctx.fill();
        });
        ctx.fillStyle = 'rgba(242,234,214,0.7)'; ctx.fillRect(0, 330, 512, 20);
        ctx.fillStyle = '#B82E24'; ctx.fillRect(420, 80, 28, 28);
        return new THREE.CanvasTexture(c);
      }

      function makeQinghuaTex() {
        const c = document.createElement('canvas'); c.width = 1024; c.height = 1024;
        const ctx = c.getContext('2d');
        ctx.fillStyle = '#F3F7FA'; ctx.fillRect(0, 0, 1024, 1024);
        const cDark = '#0F3166', cMid = '#1F5299', cLight = '#5482C4';
        const hLine = (y, w = 5) => { ctx.strokeStyle = cDark; ctx.lineWidth = w; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(1024, y); ctx.stroke(); };
        hLine(32, 5); hLine(44, 3);
        // 颈部蕉叶纹
        for (let x = 8; x < 1024; x += 42.66) {
          ctx.fillStyle = cLight; ctx.beginPath(); ctx.moveTo(x + 3, 145); ctx.quadraticCurveTo(x + 21, 45, x + 39, 145); ctx.fill();
          ctx.strokeStyle = cDark; ctx.lineWidth = 3; ctx.stroke();
        }
        hLine(152, 5);
        // 肩部如意云肩纹
        for (let i = 0; i < 8; i++) {
          const x0 = i * 128;
          ctx.fillStyle = cLight; ctx.beginPath(); ctx.moveTo(x0 + 4, 160); ctx.bezierCurveTo(x0 + 18, 290, x0 + 110, 290, x0 + 124, 160); ctx.closePath(); ctx.fill();
          ctx.strokeStyle = cDark; ctx.lineWidth = 4; ctx.stroke();
          ctx.fillStyle = cDark; ctx.beginPath(); ctx.arc(x0 + 64, 215, 18, 0, Math.PI * 2); ctx.fill();
        }
        hLine(305, 6);
        // 腹部缠枝牡丹主纹
        ctx.strokeStyle = cDark; ctx.lineWidth = 6; ctx.beginPath();
        for (let x = 0; x <= 1024; x += 8) {
          const y = 535 + Math.sin((x / 1024) * Math.PI * 6) * 120;
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.stroke();
        for (let i = 0; i < 6; i++) {
          const cx = 85 + i * 170.6, cy = 535 + (i % 2 === 0 ? -75 : 75);
          for (let p = 0; p < 10; p++) {
            const a = (p / 10) * Math.PI * 2;
            ctx.fillStyle = cLight; ctx.beginPath(); ctx.arc(cx + Math.cos(a) * 38, cy + Math.sin(a) * 38, 20, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = cDark; ctx.lineWidth = 2.5; ctx.stroke();
          }
          ctx.fillStyle = cDark; ctx.beginPath(); ctx.arc(cx, cy, 16, 0, Math.PI * 2); ctx.fill();
        }
        hLine(755, 6);
        // 胫部仰莲瓣纹
        for (let x = 0; x < 1024; x += 64) {
          ctx.fillStyle = cLight; ctx.beginPath(); ctx.moveTo(x + 6, 985); ctx.quadraticCurveTo(x + 32, 770, x + 58, 985); ctx.closePath(); ctx.fill();
          ctx.strokeStyle = cDark; ctx.lineWidth = 4; ctx.stroke();
        }
        hLine(992, 5);
        const t = new THREE.CanvasTexture(c);
        t.wrapS = THREE.RepeatWrapping;
        return t;
      }

      const MAT = {
        walnut: new THREE.MeshStandardMaterial({ map: makeWoodTex('#50311B', '#231106'), roughness: 0.44, metalness: 0.04 }),
        walnutDark: new THREE.MeshStandardMaterial({ map: makeWoodTex('#341E0F', '#140903'), roughness: 0.50, metalness: 0.04 }),
        pearwood: new THREE.MeshStandardMaterial({ map: makeWoodTex('#7E4F2C', '#4A2B13'), roughness: 0.52 }),
        brass: new THREE.MeshStandardMaterial({ color: 0xCFA354, roughness: 0.26, metalness: 0.86 }),
        bronze: new THREE.MeshStandardMaterial({ color: 0x473829, roughness: 0.34, metalness: 0.82 }),
        silver: new THREE.MeshStandardMaterial({ color: 0xE2E4E6, roughness: 0.30, metalness: 0.80 }),
        glass: new THREE.MeshStandardMaterial({ color: 0xE8F6FA, transparent: true, opacity: 0.28, roughness: 0.06, metalness: 0.1 }),
        brocade: new THREE.MeshStandardMaterial({ color: 0xEBE1CF, roughness: 0.76 }),
        crimson: new THREE.MeshStandardMaterial({ color: 0xB2261E, roughness: 0.65 }),
        papercutRed: new THREE.MeshStandardMaterial({ color: 0xC8251D, roughness: 0.72, side: THREE.DoubleSide }),
        jade: new THREE.MeshStandardMaterial({ color: 0x68A890, roughness: 0.18, metalness: 0.05 }),
        ruCeladon: new THREE.MeshStandardMaterial({ color: 0x8FB5AC, roughness: 0.14, metalness: 0.05 }),
        water: new THREE.MeshStandardMaterial({ color: 0xD4F0EC, transparent: true, opacity: 0.6, roughness: 0.05 }),
        teaLiquid: new THREE.MeshStandardMaterial({ color: 0xB86B28, transparent: true, opacity: 0.82, roughness: 0.08 }),
        inkstone: new THREE.MeshStandardMaterial({ color: 0x242021, roughness: 0.42 }),
        inkLiquid: new THREE.MeshStandardMaterial({ color: 0x080808, roughness: 0.05 }),
        whiteGlaze: new THREE.MeshStandardMaterial({ color: 0xF2F6FA, roughness: 0.09, metalness: 0.04 }),
        qinghuaGlaze: new THREE.MeshStandardMaterial({ map: makeQinghuaTex(), roughness: 0.09, metalness: 0.04 }),
        bisque: new THREE.MeshStandardMaterial({ color: 0xD6C2A5, roughness: 0.86 }),
        burntOrange: new THREE.MeshStandardMaterial({ color: 0xB85D38, roughness: 0.75 }),
        ruimaoPrint: new THREE.MeshStandardMaterial({ map: makeRuimaoTex(), roughness: 0.68, side: THREE.DoubleSide }),
        bianEmbroidery: new THREE.MeshStandardMaterial({ map: makeBianSilkTex(), roughness: 0.55 }),
        songSilk: new THREE.MeshStandardMaterial({ map: makeSongLandscapeTex(0), roughness: 0.65, side: THREE.DoubleSide }),
        lanternSilk: new THREE.MeshStandardMaterial({
          map: makeSongLandscapeTex(1), emissive: 0xFF9D3B, emissiveIntensity: 0.35, roughness: 0.45, side: THREE.DoubleSide
        }),
        lotusPetal: new THREE.MeshStandardMaterial({
          color: 0xFFF5E0, emissive: 0xFF9A36, emissiveIntensity: 0.55, roughness: 0.35, side: THREE.DoubleSide
        }),
        glowCore: new THREE.MeshStandardMaterial({ color: 0xFFF8E8, emissive: 0xFFB246, emissiveIntensity: 2.2 }),
        azuriteRock: new THREE.MeshStandardMaterial({ color: 0x1C4E78, roughness: 0.78 }),
        malachiteRock: new THREE.MeshStandardMaterial({ color: 0x287A60, roughness: 0.76 }),
        cinnabar: new THREE.MeshStandardMaterial({ color: 0xC42E23, roughness: 0.85 }),
        ochreRock: new THREE.MeshStandardMaterial({ color: 0xB87333, roughness: 0.82 })
      };

      function box(w, h, d, mat, x = 0, y = 0, z = 0, parent = null, name = '') {
        const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
        if (name) m.name = name;
        m.position.set(x, y, z);
        m.castShadow = true; m.receiveShadow = true;
        if (parent) parent.add(m);
        return m;
      }

      function cyl(rTop, rBot, h, segs, mat, x = 0, y = 0, z = 0, parent = null, name = '') {
        const m = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBot, h, segs), mat);
        if (name) m.name = name;
        m.position.set(x, y, z);
        m.castShadow = true; m.receiveShadow = true;
        if (parent) parent.add(m);
        return m;
      }

      function addFlushSpandrel(parent, x, y, z, dirX = 1, dirY = -1, mat = MAT.walnutDark) {
        const g = new THREE.Group();
        g.position.set(x, y, z);
        box(0.052, 0.010, 0.016, mat, dirX * 0.026, dirY * 0.005, 0, g);
        box(0.010, 0.052, 0.016, mat, dirX * 0.005, dirY * 0.026, 0, g);
        box(0.028, 0.008, 0.016, mat, dirX * 0.020, dirY * 0.022, 0, g);
        parent.add(g);
      }

export const PROP_BUILDERS: Record<string, () => THREE.Group> = {
  DIY_A01: () => {
          const root = new THREE.Group(); root.name = 'DIY_A01_bogujia_walnut';
          const W = 1.20, D = 0.36, H = 1.85, postX = 0.56, postZ = 0.15;
          box(W - 0.02, 0.024, 0.036, MAT.walnutDark, 0, 0.012, postZ, root);
          box(W - 0.02, 0.024, 0.036, MAT.walnutDark, 0, 0.012, -postZ, root);
          [-postX, postX].forEach(sx => {
            box(0.036, 0.024, D - 0.02, MAT.walnutDark, sx, 0.012, 0, root);
            [-postZ, postZ].forEach(sz => {
              box(0.040, H - 0.03, 0.040, MAT.walnut, sx, (H + 0.02) / 2, sz, root);
              box(0.050, 0.038, 0.050, MAT.walnutDark, sx, 0.038, sz, root);
            });
          });
          const cD = D - 0.02;
          box(W - 0.04, 0.026, cD, MAT.walnut, 0, 0.12, 0, root);
          box(W - 0.04, 0.024, cD, MAT.walnut, 0, 0.35, 0, root);
          box(W, 0.030, D, MAT.walnut, 0, 0.48, 0, root);
          box(W - 0.06, 0.36, 0.014, MAT.walnutDark, 0, 0.30, -postZ + 0.01, root);
          box(0.028, 0.36, cD - 0.01, MAT.walnut, 0, 0.30, 0, root);
          const doorL = new THREE.Group(); doorL.name = 'Cabinet_Door_L'; doorL.position.set(-0.54, 0.235, postZ);
          box(0.525, 0.20, 0.020, MAT.walnutDark, 0.2625, 0, 0, doorL);
          const doorR = new THREE.Group(); doorR.name = 'Cabinet_Door_R'; doorR.position.set(0.54, 0.235, postZ);
          box(0.525, 0.20, 0.020, MAT.walnutDark, -0.2625, 0, 0, doorR);
          cyl(0.028, 0.028, 0.008, 20, MAT.brass, 0.51, 0, 0.012, doorL).rotation.x = Math.PI / 2;
          cyl(0.028, 0.028, 0.008, 20, MAT.brass, -0.51, 0, 0.012, doorR).rotation.x = Math.PI / 2;
          root.add(doorL, doorR);
          const drawL = box(0.52, 0.092, cD - 0.02, MAT.walnutDark, -0.275, 0.415, 0, root, 'Drawer_Left');
          const drawR = box(0.52, 0.092, cD - 0.02, MAT.walnutDark,  0.275, 0.415, 0, root, 'Drawer_Right');
          [[-postX, 0.12, 0.80], [-0.18, postX, 0.98], [-postX, 0.22, 1.18], [-0.22, postX, 1.36], [-postX, postX, 1.56], [-0.60, 0.60, 1.82]].forEach(([x1, x2, y], i) => {
            box(x2 - x1, 0.024, D - 0.03, MAT.walnut, (x1 + x2) / 2, y, 0, root, `Snap_Slot_0${i + 1}`);
          });
          [[0.12, 0.48, 0.98], [-0.18, 0.80, 1.18], [0.22, 0.98, 1.36], [-0.22, 1.18, 1.56], [0.14, 1.56, 1.82], [-0.28, 1.56, 1.82]].forEach(([vx, y1, y2]) => {
            box(0.024, y2 - y1, D - 0.04, MAT.walnut, vx, (y1 + y2) / 2, 0, root);
          });
          root.userData.interact = t => {
            const p = (Math.sin(t) * 0.5 + 0.5) * 0.14;
            drawL.position.z = p; drawR.position.z = (Math.cos(t) * 0.5 + 0.5) * 0.14;
            doorL.rotation.y = -p * 3.5; doorR.rotation.y = p * 3.5;
          };
          return root;
        },
  DIY_A02: () => {
          const root = new THREE.Group(); root.name = 'DIY_A02_display_case_cloud';
          const W = 0.80, D = 0.80, Hb = 0.76, Hh = 0.69;
          [-0.35, 0.35].forEach(sx => [-0.35, 0.35].forEach(sz => {
            box(0.068, 0.34, 0.068, MAT.walnut, sx, 0.18, sz, root);
            box(0.078, 0.042, 0.078, MAT.brass, sx, 0.042, sz, root);
          }));
          box(W, 0.30, D, MAT.walnut, 0, 0.49, 0, root);
          box(W - 0.06, 0.07, D - 0.06, MAT.walnutDark, 0, 0.675, 0, root);
          box(W + 0.02, 0.05, D + 0.02, MAT.walnut, 0, 0.735, 0, root);
          box(0.68, 0.030, 0.68, MAT.brocade, 0, Hb + 0.015, 0, root);
          box(0.38, 0.045, 0.38, MAT.crimson, 0, Hb + 0.052, -0.03, root, 'Inner_Display_Mount');
          const hood = new THREE.Group(); hood.name = 'Glass_Hood_Liftable'; hood.position.set(0, Hb + Hh / 2, 0);
          const gw = W - 0.04, gd = D - 0.04;
          box(gw, Hh, gd, MAT.glass, 0, 0, 0, hood);
          [-gw / 2, gw / 2].forEach(sx => [-gd / 2, gd / 2].forEach(sz => {
            box(0.018, Hh + 0.01, 0.018, MAT.bronze, sx, 0, sz, hood);
            cyl(0.007, 0.007, 0.35, 12, MAT.brass, sx * 0.94, -Hh / 2 - 0.17, sz * 0.94, hood);
          }));
          box(0.38, 0.015, 0.38, MAT.glowCore, 0, Hh / 2 - 0.015, 0, hood);
          root.add(hood);
          root.userData.interact = t => { hood.position.y = Hb + Hh / 2 + (Math.sin(t) * 0.5 + 0.5) * 0.26; };
          return root;
        },
  DIY_A04: () => {
          const root = new THREE.Group(); root.name = 'DIY_A04_folding_screen_song';
          const leafW = 0.45, leafH = 1.75, leafT = 0.032, leaves = [];
          for (let i = 0; i < 4; i++) {
            const leaf = new THREE.Group(); leaf.name = `Screen_Leaf_0${i + 1}`;
            const cx = leafW / 2;
            [0.018, leafW - 0.018].forEach(lx => {
              box(0.036, leafH, leafT, MAT.walnut, lx, leafH / 2, 0, leaf);
              box(0.044, 0.065, 0.048, MAT.brass, lx, 0.0325, 0, leaf);
            });
            [leafH - 0.018, 1.48, 0.38, 0.12].forEach(ly => box(leafW, 0.034, leafT, MAT.walnut, cx, ly, 0, leaf));
            box(leafW - 0.06, 1.07, 0.014, MAT.brocade, cx, 0.93, 0, leaf);
            const sMat = new THREE.MeshStandardMaterial({ map: makeSongLandscapeTex(i * 1.4), roughness: 0.72 });
            box(leafW - 0.11, 0.96, 0.018, sMat, cx, 0.93, 0, leaf);
            box(leafW - 0.06, 0.23, 0.018, MAT.walnutDark, cx, 0.25, 0, leaf);
            leaves.push(leaf); root.add(leaf);
          }
          const updatePose = a => {
            const angs = [a, -a, a, -a];
            let currX = -leafW * 2 * Math.cos(a), currZ = -Math.sin(a) * leafW * 0.5;
            leaves.forEach((l, i) => {
              l.position.set(currX, 0, currZ); l.rotation.y = angs[i];
              currX += leafW * Math.cos(angs[i]); currZ -= leafW * Math.sin(angs[i]);
            });
          };
          updatePose(0.24);
          root.userData.interact = t => updatePose(0.12 + (Math.sin(t * 0.8) * 0.5 + 0.5) * 0.34);
          return root;
        },
  DIY_A05: () => {
          const root = new THREE.Group(); root.name = 'DIY_A05_floor_lamp_lotus';
          cyl(0.19, 0.21, 0.036, 40, MAT.walnutDark, 0, 0.018, 0, root);
          cyl(0.07, 0.17, 0.07, 32, MAT.brass, 0, 0.065, 0, root);
          cyl(0.017, 0.022, 1.24, 28, MAT.walnut, 0, 0.72, 0, root);
          box(0.14, 0.018, 0.018, MAT.walnutDark, 0.07, 1.25, 0, root);
          box(0.095, 0.014, 0.014, MAT.walnut, 0.042, 1.215, 0, root).rotation.z = 0.68;
          const tassel = new THREE.Group(); tassel.name = 'Jade_Tassel_Switch'; tassel.position.set(0.138, 1.24, 0);
          cyl(0.0025, 0.0025, 0.14, 8, MAT.crimson, 0, -0.07, 0, tassel);
          const jb = new THREE.Mesh(new THREE.SphereGeometry(0.015, 16, 16), MAT.jade); jb.position.y = -0.11; tassel.add(jb);
          cyl(0.014, 0.024, 0.085, 20, MAT.crimson, 0, -0.185, 0, tassel); root.add(tassel);
          const lotusG = new THREE.Group(); lotusG.name = 'Lotus_Shade_24Petals'; lotusG.position.set(0, 1.33, 0);
          cyl(0.068, 0.020, 0.042, 24, MAT.brass, 0, 0.021, 0, lotusG);
          cyl(0.052, 0.032, 0.065, 24, MAT.glowCore, 0, 0.065, 0, lotusG, 'Lotus_Seedpod_Core');
          const petalGeo = new THREE.SphereGeometry(0.055, 16, 16, 0, Math.PI, 0, Math.PI * 0.82);
          petalGeo.scale(0.62, 1.85, 0.28); petalGeo.translate(0, 0.075, 0);
          [[0.038, 0.28, 0], [0.050, 0.56, Math.PI / 8], [0.060, 0.86, 0]].forEach(([r, tilt, off]) => {
            for (let i = 0; i < 8; i++) {
              const pH = new THREE.Group(); pH.rotation.y = (i / 8) * Math.PI * 2 + off;
              const p = new THREE.Mesh(petalGeo, MAT.lotusPetal); p.position.set(0, 0.028, r); p.rotation.x = tilt;
              pH.add(p); lotusG.add(pH);
            }
          });
          root.add(lotusG);
          root.userData.interact = t => { tassel.rotation.z = Math.sin(t * 2.5) * 0.09; };
          return root;
        },
  DIY_A07: () => {
          const root = new THREE.Group(); root.name = 'DIY_A07_palace_lantern_hex';
          const bodyG = new THREE.Group(); bodyG.name = 'Lantern_Body_Pivot';
          root.add(bodyG);
          const R = 0.20, yBot = 0.26, yTop = 0.68, hSpan = yTop - yBot;
          const topHook = new THREE.Mesh(new THREE.TorusGeometry(0.024, 0.005, 10, 20), MAT.brass);
          topHook.name = 'Top_Suspension_Hook'; topHook.position.set(0, 0.835, 0);
          bodyG.add(topHook);
          cyl(0.036, 0.085, 0.055, 6, MAT.walnutDark, 0, 0.73, 0, bodyG);
          cyl(0.006, 0.006, 0.11, 12, MAT.brass, 0, 0.78, 0, bodyG);
          cyl(R + 0.025, R + 0.015, 0.028, 6, MAT.walnut, 0, yTop, 0, bodyG);
          cyl(R + 0.015, R + 0.025, 0.028, 6, MAT.walnut, 0, yBot, 0, bodyG);
          cyl(R * 0.75, R * 0.55, 0.035, 6, MAT.walnutDark, 0, yBot - 0.025, 0, bodyG);
          const glowCore = cyl(0.048, 0.048, hSpan * 0.65, 20, MAT.glowCore, 0, (yTop + yBot) / 2, 0, bodyG, 'Core_Candle_Light');
          const tasselG = new THREE.Group(); tasselG.name = 'Bottom_Tassels_Group';
          bodyG.add(tasselG);
          for (let i = 0; i < 6; i++) {
            const ang = (i / 6) * Math.PI * 2;
            const px = Math.cos(ang) * R, pz = Math.sin(ang) * R;
            cyl(0.011, 0.011, hSpan + 0.02, 12, MAT.walnutDark, px, (yTop + yBot) / 2, pz, bodyG);
            const eaveTop = box(0.048, 0.014, 0.014, MAT.brass, px * 1.12, yTop + 0.008, pz * 1.12, bodyG);
            eaveTop.rotation.y = -ang;
            cyl(0.002, 0.002, 0.05, 8, MAT.crimson, px * 1.15, yBot - 0.03, pz * 1.15, tasselG);
            cyl(0.008, 0.014, 0.07, 12, MAT.crimson, px * 1.15, yBot - 0.09, pz * 1.15, tasselG);
            const midAng = ang + Math.PI / 6;
            const apothem = R * Math.cos(Math.PI / 6);
            const sideW = 2 * R * Math.sin(Math.PI / 6) - 0.016;
            const panelG = new THREE.Group();
            panelG.position.set(Math.cos(midAng) * apothem, (yTop + yBot) / 2, Math.sin(midAng) * apothem);
            panelG.rotation.y = -midAng + Math.PI / 2;
            box(sideW, hSpan - 0.02, 0.004, MAT.lanternSilk, 0, 0, 0, panelG);
            box(sideW, 0.032, 0.008, MAT.walnutDark, 0, hSpan / 2 - 0.024, 0, panelG);
            box(sideW, 0.032, 0.008, MAT.walnutDark, 0, -hSpan / 2 + 0.024, 0, panelG);
            bodyG.add(panelG);
          }
          cyl(0.003, 0.003, 0.08, 10, MAT.crimson, 0, 0.20, 0, tasselG);
          const centerJade = new THREE.Mesh(new THREE.SphereGeometry(0.018, 16, 16), MAT.jade);
          centerJade.position.set(0, 0.16, 0); tasselG.add(centerJade);
          cyl(0.014, 0.028, 0.13, 20, MAT.crimson, 0, 0.085, 0, tasselG);
          root.userData.interact = t => {
            bodyG.rotation.y = t * 0.35;
            tasselG.rotation.z = Math.sin(t * 2.2) * 0.05;
          };
          return root;
        },
  DIY_A09: () => {
          const root = new THREE.Group(); root.name = 'DIY_A09_plaque_stand_song';
          box(0.32, 0.032, 0.24, MAT.walnutDark, 0, 0.016, 0, root, 'Pedestal_Base');
          box(0.26, 0.036, 0.18, MAT.walnut, 0, 0.050, 0, root);
          cyl(0.045, 0.065, 0.04, 24, MAT.brass, 0, 0.088, 0, root);
          cyl(0.018, 0.022, 0.86, 24, MAT.walnut, 0, 0.52, 0, root);
          const boardG = new THREE.Group(); boardG.name = 'Tilted_Plaque_Board';
          boardG.position.set(0, 0.96, 0); boardG.rotation.x = -0.58;
          box(0.38, 0.26, 0.022, MAT.walnutDark, 0, 0, 0, boardG);
          box(0.33, 0.21, 0.026, MAT.brocade, 0, 0, 0.002, boardG, 'Dynamic_Text_Surface');
          box(0.34, 0.008, 0.028, MAT.brass, 0, 0.07, 0.002, boardG);
          root.add(boardG);
          root.userData.interact = t => { boardG.rotation.x = -0.58 + Math.sin(t * 1.5) * 0.12; };
          return root;
        },
  DIY_B02: () => {
          const root = new THREE.Group(); root.name = 'DIY_B02_woodblock_printing_table';
          const W = 1.20, D = 0.65, H = 0.78;
          box(W, 0.034, D, MAT.walnut, 0, H - 0.017, 0, root);
          [-0.52, 0.52].forEach(sx => {
            [-0.26, 0.26].forEach(sz => box(0.046, H - 0.03, 0.046, MAT.walnut, sx, (H - 0.03) / 2, sz, root));
            box(0.032, 0.032, 0.52, MAT.walnutDark, sx, 0.24, 0, root);
          });
          box(1.04, 0.020, 0.46, MAT.pearwood, 0, 0.255, 0, root);
          box(0.42, 0.035, 0.32, MAT.brocade, -0.22, 0.282, 0, root);
          const blockG = new THREE.Group(); blockG.name = 'Carved_Master_Block'; blockG.position.set(-0.18, H, 0.02);
          box(0.36, 0.032, 0.36, MAT.pearwood, 0, 0.016, 0, blockG);
          box(0.32, 0.008, 0.32, MAT.inkstone, 0, 0.034, 0, blockG);
          [[-0.20, -0.20], [-0.20, 0.20], [0.20, -0.20]].forEach(([wx, wz]) => box(0.035, 0.024, 0.035, MAT.walnutDark, wx, 0.012, wz, blockG));
          root.add(blockG);
          box(0.036, 0.028, 0.38, MAT.walnutDark, 0.03, H + 0.014, 0.02, root);
          box(0.024, 0.016, 0.36, MAT.brass, 0.03, H + 0.032, 0.02, root);
          const paperGeo = new THREE.PlaneGeometry(0.34, 0.34, 24, 1);
          const updatePaper = lift => {
            const pos = paperGeo.attributes.position;
            for (let i = 0; i < pos.count; i++) {
              const u = Math.max(0, (0.17 - pos.getX(i)) / 0.34);
              pos.setZ(i, Math.pow(u, 1.6) * (0.04 + lift * 0.14));
            }
            paperGeo.computeVertexNormals(); pos.needsUpdate = true;
          };
          updatePaper(0.6);
          const paperMesh = new THREE.Mesh(paperGeo, MAT.ruimaoPrint);
          paperMesh.name = 'Peeling_Print_Paper'; paperMesh.rotation.x = -Math.PI / 2;
          paperMesh.position.set(-0.15, H + 0.038, 0.02); root.add(paperMesh);
          const baren = new THREE.Group(); baren.name = 'Palm_Baren_Tool'; baren.position.set(0.32, H, 0.12);
          cyl(0.035, 0.042, 0.028, 20, MAT.walnutDark, 0, 0.014, 0, baren);
          box(0.11, 0.022, 0.028, MAT.pearwood, 0, 0.035, 0, baren); root.add(baren);
          [[0.30, -0.10, MAT.crimson], [0.42, -0.06, MAT.malachiteRock]].forEach(([bx, bz, pMat]) => {
            cyl(0.045, 0.034, 0.032, 24, MAT.whiteGlaze, bx, H + 0.016, bz, root);
            cyl(0.038, 0.038, 0.006, 20, pMat, bx, H + 0.028, bz, root);
          });
          root.userData.interact = t => updatePaper(Math.sin(t * 1.5) * 0.5 + 0.5);
          return root;
        },
  DIY_C02: () => {
          const root = new THREE.Group(); root.name = 'DIY_C02_silk_thread_rack_bian';
          const W = 0.76, D = 0.28, H = 0.88;
          [-0.33, 0.33].forEach(sx => {
            box(0.048, 0.036, D, MAT.walnutDark, sx, 0.018, 0, root);
            cyl(0.055, 0.055, 0.042, 24, MAT.walnut, sx, 0.055, 0.08, root).rotation.z = Math.PI / 2;
            cyl(0.055, 0.055, 0.042, 24, MAT.walnut, sx, 0.055, -0.08, root).rotation.z = Math.PI / 2;
            box(0.038, H - 0.04, 0.038, MAT.walnut, sx, (H - 0.04) / 2, 0, root);
          });
          box(W, 0.036, 0.045, MAT.walnut, 0, H - 0.025, 0, root);
          box(0.66, 0.065, 0.024, MAT.walnutDark, 0, 0.12, 0, root);
          const silkPalette = [
            [0x8B1E16, 0xB8281E, 0xD94838, 0xE87A68, 0xF2A898, 0xF8D0C4],
            [0xB87A1E, 0xD99B26, 0xE8B842, 0xF2D06B, 0x9E7852, 0x6E4E32],
            [0x184D3E, 0x246E58, 0x328E72, 0x52B092, 0x78C8AC, 0xA8E0CA],
            [0x122E52, 0x1C487A, 0x2B68A6, 0x4E8AC8, 0x5E4B8B, 0x8C78B8]
          ];
          const spoolRows = [];
          [0.27, 0.43, 0.59, 0.75].forEach((ry, rIdx) => {
            const rowG = new THREE.Group(); rowG.name = `Spool_Row_${rIdx + 1}`; rowG.position.set(0, ry, 0);
            cyl(0.006, 0.006, 0.68, 16, MAT.brass, 0, 0, 0, rowG).rotation.z = Math.PI / 2;
            for (let c = 0; c < 6; c++) {
              const sx = -0.24 + c * 0.096;
              const spoolG = new THREE.Group(); spoolG.position.set(sx, 0, 0);
              cyl(0.036, 0.036, 0.007, 24, MAT.pearwood, -0.032, 0, 0, spoolG).rotation.z = Math.PI / 2;
              cyl(0.036, 0.036, 0.007, 24, MAT.pearwood,  0.032, 0, 0, spoolG).rotation.z = Math.PI / 2;
              const tMat = new THREE.MeshStandardMaterial({ color: silkPalette[rIdx][c], roughness: 0.35, metalness: 0.12 });
              cyl(0.031, 0.031, 0.058, 24, tMat, 0, 0, 0, spoolG).rotation.z = Math.PI / 2;
              rowG.add(spoolG);
            }
            spoolRows.push(rowG); root.add(rowG);
          });
          root.userData.interact = t => spoolRows.forEach((r, i) => { r.rotation.x = t * (i % 2 === 0 ? 1.2 : -1.2); });
          return root;
        },
  DIY_D01: () => {
          const root = new THREE.Group(); root.name = 'DIY_D01_painting_desk_mineral';
          const W = 1.35, D = 0.68, H = 0.78;
          box(W, 0.028, D, MAT.walnut, 0, H - 0.014, 0, root);
          box(W - 0.03, 0.020, D - 0.03, MAT.walnutDark, 0, H - 0.034, 0, root);
          [-0.25, 0.25].forEach(sz => box(1.14, 0.052, 0.022, MAT.walnutDark, 0, H - 0.070, sz, root));
          [-0.55, 0.55].forEach(sx => {
            [-0.25, 0.25].forEach(sz => cyl(0.025, 0.021, H - 0.028, 24, MAT.walnut, sx, (H - 0.028) / 2, sz, root));
            box(0.030, 0.028, 0.50, MAT.walnutDark, sx, 0.24, 0, root);
            box(0.030, 0.028, 0.50, MAT.walnutDark, sx, 0.40, 0, root);
          });
          const scrollG = new THREE.Group(); scrollG.name = 'Scroll_Painting_Roll'; scrollG.position.set(-0.20, H, 0.03);
          box(0.72, 0.004, 0.38, MAT.brocade, 0, 0.002, 0, scrollG);
          box(0.56, 0.006, 0.32, MAT.songSilk, 0.02, 0.004, 0, scrollG);
          cyl(0.022, 0.022, 0.39, 24, MAT.brocade, -0.35, 0.022, 0, scrollG).rotation.x = Math.PI / 2;
          box(0.022, 0.014, 0.24, MAT.brass, -0.18, 0.010, -0.01, scrollG);
          box(0.022, 0.014, 0.24, MAT.brass,  0.25, 0.010,  0.01, scrollG);
          root.add(scrollG);
          const boxG = new THREE.Group(); boxG.position.set(0.36, H, 0.11);
          box(0.28, 0.044, 0.20, MAT.walnutDark, 0, 0.022, 0, boxG);
          [[-0.09, -0.046, MAT.azuriteRock], [0, -0.046, MAT.malachiteRock], [-0.09, 0.046, MAT.cinnabar], [0, 0.046, MAT.ochreRock]].forEach(([px, pz, m]) => {
            cyl(0.033, 0.025, 0.018, 20, MAT.whiteGlaze, px, 0.046, pz, boxG);
            cyl(0.026, 0.005, 0.015, 16, m, px, 0.056, pz, boxG);
          });
          const lidPivot = new THREE.Group(); lidPivot.name = 'Mineral_Box_Lid'; lidPivot.position.set(0, 0.044, -0.10);
          box(0.28, 0.016, 0.20, MAT.walnut, 0, 0.008, 0.10, lidPivot);
          lidPivot.rotation.x = -1.65; boxG.add(lidPivot); root.add(boxG);
          box(0.18, 0.16, 0.03, MAT.walnutDark, 0.26, H + 0.08, -0.18, root, 'Brush_Rack_With_Brushes');
          box(0.11, 0.024, 0.15, MAT.inkstone, 0.43, H + 0.012, -0.18, root, 'Duan_Inkstone');
          cyl(0.046, 0.036, 0.032, 24, MAT.ruCeladon, 0.10, H + 0.016, -0.18, root, 'Ru_Kiln_Washer');
          root.userData.interact = t => { lidPivot.rotation.x = -0.2 - (Math.sin(t) * 0.5 + 0.5) * 1.45; };
          return root;
        },
  DIY_D04: () => {
          const root = new THREE.Group(); root.name = 'DIY_D04_landscape_diorama_song';
          box(0.52, 0.022, 0.32, MAT.walnutDark, 0, 0.011, 0, root);
          box(0.48, 0.018, 0.28, MAT.walnut, 0, 0.030, 0, root);
          box(0.50, 0.018, 0.30, MAT.walnutDark, 0, 0.046, 0, root);
          box(0.46, 0.008, 0.26, MAT.jade, 0, 0.056, 0, root);
          [
            [-0.06, -0.03, 0.095, 0.31, MAT.azuriteRock, 'Main_Azurite_Peak'],
            [-0.15,  0.02, 0.075, 0.22, MAT.malachiteRock, ''],
            [ 0.11, -0.02, 0.082, 0.16, MAT.malachiteRock, 'Cliff_Platform_Peak'],
            [ 0.17,  0.04, 0.062, 0.12, MAT.ochreRock, ''],
            [-0.02,  0.06, 0.058, 0.10, MAT.ochreRock, '']
          ].forEach(([x, z, r, h, m, n]) => {
            cyl(r * 0.28, r, h, 7, m, x, 0.055 + h / 2, z, root, n).rotation.y = x * 3;
          });
          const pavG = new THREE.Group(); pavG.name = 'Pavilion_Mini_Roof'; pavG.position.set(0.11, 0.215, -0.02);
          box(0.068, 0.012, 0.068, MAT.walnutDark, 0, 0.006, 0, pavG);
          [-0.024, 0.024].forEach(px => [-0.024, 0.024].forEach(pz => cyl(0.003, 0.003, 0.048, 8, MAT.crimson, px, 0.036, pz, pavG)));
          const roof = new THREE.Mesh(new THREE.ConeGeometry(0.058, 0.036, 4), MAT.walnutDark);
          roof.rotation.y = Math.PI / 4; roof.position.y = 0.075; pavG.add(roof);
          root.add(pavG);
          const bridge = new THREE.Mesh(new THREE.TorusGeometry(0.038, 0.008, 10, 20, Math.PI), MAT.brocade);
          bridge.name = 'Arch_Bridge_Stone'; bridge.position.set(0.03, 0.056, 0.05); root.add(bridge);
          const cloudG = new THREE.Group(); cloudG.name = 'Cloud_Mist_Layer'; cloudG.position.set(-0.05, 0.21, 0.03);
          [-0.04, 0, 0.045].forEach((cx, i) => {
            const cBall = new THREE.Mesh(new THREE.SphereGeometry(0.026 - i * 0.003, 16, 12), MAT.whiteGlaze);
            cBall.scale.set(1.5, 0.55, 0.8); cBall.position.set(cx, i * 0.006, 0); cloudG.add(cBall);
          });
          root.add(cloudG);
          root.userData.interact = t => { cloudG.position.x = -0.05 + Math.sin(t * 1.5) * 0.025; };
          return root;
        },
  DIY_E01: () => {
          const root = new THREE.Group(); root.name = 'DIY_E01_meiping_vase_qinghua';
          const standPts = [new THREE.Vector2(0, 0.038), new THREE.Vector2(0.068, 0.038), new THREE.Vector2(0.070, 0.045), new THREE.Vector2(0.082, 0.042), new THREE.Vector2(0.084, 0.022), new THREE.Vector2(0.068, 0.004), new THREE.Vector2(0, 0.004)];
          const stand = new THREE.Mesh(new THREE.LatheGeometry(standPts, 48), MAT.walnutDark);
          stand.name = 'Rosewood_FiveFoot_Stand'; root.add(stand);
          const footPts = [new THREE.Vector2(0, 0.046), new THREE.Vector2(0.056, 0.046), new THREE.Vector2(0.060, 0.038), new THREE.Vector2(0.066, 0.038), new THREE.Vector2(0.068, 0.052)];
          const foot = new THREE.Mesh(new THREE.LatheGeometry(footPts, 64), MAT.bisque);
          foot.name = 'Meiping_Foot_Bisque'; root.add(foot);
          const outerPts = [
            new THREE.Vector2(0.068, 0.052), new THREE.Vector2(0.071, 0.085), new THREE.Vector2(0.078, 0.130),
            new THREE.Vector2(0.092, 0.185), new THREE.Vector2(0.109, 0.245), new THREE.Vector2(0.119, 0.295),
            new THREE.Vector2(0.121, 0.325), new THREE.Vector2(0.112, 0.355), new THREE.Vector2(0.090, 0.378),
            new THREE.Vector2(0.055, 0.392), new THREE.Vector2(0.027, 0.400), new THREE.Vector2(0.028, 0.412),
            new THREE.Vector2(0.033, 0.420), new THREE.Vector2(0.032, 0.424)
          ];
          const outerGeo = new THREE.LatheGeometry(outerPts, 64);
          const pos = outerGeo.attributes.position, uv = outerGeo.attributes.uv;
          for (let i = 0; i < pos.count; i++) {
            uv.setY(i, Math.max(0.002, Math.min(0.998, (pos.getY(i) - 0.052) / (0.424 - 0.052))));
          }
          outerGeo.computeVertexNormals();
          const outer = new THREE.Mesh(outerGeo, MAT.qinghuaGlaze);
          outer.name = 'Meiping_Outer_Glaze'; outer.castShadow = true; root.add(outer);
          const innerPts = [new THREE.Vector2(0.032, 0.424), new THREE.Vector2(0.027, 0.426), new THREE.Vector2(0.022, 0.422), new THREE.Vector2(0.020, 0.395), new THREE.Vector2(0.045, 0.350), new THREE.Vector2(0, 0.340)];
          const inner = new THREE.Mesh(new THREE.LatheGeometry(innerPts, 64), MAT.whiteGlaze);
          inner.name = 'Meiping_Inner_WhiteGlaze'; root.add(inner);
          root.userData.interact = t => { root.rotation.y = t * 0.45; };
          return root;
        },
  DIY_E02: () => {
          const root = new THREE.Group(); root.name = 'DIY_E02_tea_set_qinghua';
          const W = 0.46, D = 0.30;
          box(W, 0.032, D, MAT.walnutDark, 0, 0.016, 0, root);
          box(W - 0.04, 0.012, D - 0.04, MAT.walnut, 0, 0.030, 0, root);
          for (let gx = -0.18; gx <= 0.18; gx += 0.036) box(0.018, 0.006, D - 0.06, MAT.pearwood, gx, 0.036, 0, root);
          const potG = new THREE.Group(); potG.name = 'Teapot_Full'; potG.position.set(-0.09, 0.038, 0);
          cyl(0.048, 0.052, 0.012, 32, MAT.bisque, 0, 0.006, 0, potG);
          const bodyPts = [new THREE.Vector2(0.048, 0.010), new THREE.Vector2(0.076, 0.045), new THREE.Vector2(0.078, 0.082), new THREE.Vector2(0.052, 0.112), new THREE.Vector2(0.042, 0.118)];
          potG.add(new THREE.Mesh(new THREE.LatheGeometry(bodyPts, 48), MAT.qinghuaGlaze));
          cyl(0.009, 0.018, 0.075, 20, MAT.whiteGlaze, -0.088, 0.082, 0, potG).rotation.z = 0.68;
          [-0.052, 0.052].forEach(sz => box(0.014, 0.024, 0.010, MAT.whiteGlaze, 0, 0.115, sz, potG));
          const archHandle = new THREE.Mesh(new THREE.TorusGeometry(0.062, 0.0055, 12, 32, Math.PI), MAT.brass);
          archHandle.rotation.y = Math.PI / 2; archHandle.position.set(0, 0.120, 0); potG.add(archHandle);
          const lidG = new THREE.Group(); lidG.name = 'Teapot_Lid_Liftable'; lidG.position.set(0, 0.118, 0);
          cyl(0.038, 0.038, 0.010, 32, MAT.whiteGlaze, 0, -0.004, 0, lidG);
          cyl(0.044, 0.046, 0.010, 32, MAT.qinghuaGlaze, 0, 0.005, 0, lidG);
          const knob = new THREE.Mesh(new THREE.SphereGeometry(0.011, 16, 16), MAT.brass); knob.position.y = 0.016; lidG.add(knob);
          potG.add(lidG); root.add(potG);
          [[0.08, -0.06], [0.17, -0.06], [0.08, 0.06], [0.17, 0.06]].forEach(([cx, cz], idx) => {
            const cupG = new THREE.Group(); cupG.name = `Teacup_0${idx + 1}`; cupG.position.set(cx, 0.038, cz);
            cyl(0.038, 0.028, 0.008, 24, MAT.walnutDark, 0, 0.004, 0, cupG);
            const cupPts = [new THREE.Vector2(0.016, 0.008), new THREE.Vector2(0.028, 0.032), new THREE.Vector2(0.032, 0.048), new THREE.Vector2(0.029, 0.048), new THREE.Vector2(0.024, 0.014), new THREE.Vector2(0.000, 0.014)];
            cupG.add(new THREE.Mesh(new THREE.LatheGeometry(cupPts, 32), MAT.qinghuaGlaze));
            cyl(0.027, 0.027, 0.002, 24, MAT.teaLiquid, 0, 0.038, 0, cupG);
            root.add(cupG);
          });
          root.userData.interact = t => {
            lidG.position.y = 0.118 + (Math.sin(t * 2) * 0.5 + 0.5) * 0.045;
          };
          return root;
        },
  DIY_E05: () => {
          const root = new THREE.Group(); root.name = 'DIY_E05_porcelain_lantern_qinghua';
          const R = 0.115;
          cyl(R + 0.018, R + 0.026, 0.028, 6, MAT.walnutDark, 0, 0.014, 0, root);
          cyl(R + 0.008, R + 0.014, 0.026, 6, MAT.walnut, 0, 0.041, 0, root);
          const bodyG = new THREE.Group(); bodyG.name = 'Porcelain_Lantern_Core'; root.add(bodyG);
          cyl(R + 0.006, R + 0.006, 0.032, 6, MAT.qinghuaGlaze, 0, 0.070, 0, bodyG);
          cyl(R + 0.006, R + 0.006, 0.032, 6, MAT.qinghuaGlaze, 0, 0.324, 0, bodyG);
          const innerGlow = cyl(0.062, 0.062, 0.25, 24, MAT.glowCore, 0, 0.195, 0, bodyG, 'Inner_Jade_Glow');
          for (let i = 0; i < 6; i++) {
            const ang = (i / 6) * Math.PI * 2;
            cyl(0.014, 0.014, 0.26, 16, MAT.qinghuaGlaze, Math.cos(ang) * R, 0.197, Math.sin(ang) * R, bodyG);
            const midAng = ang + Math.PI / 6;
            const ap = R * Math.cos(Math.PI / 6);
            const sideG = new THREE.Group();
            sideG.position.set(Math.cos(midAng) * ap, 0.197, Math.sin(midAng) * ap);
            sideG.rotation.y = -midAng + Math.PI / 2;
            box(0.095, 0.038, 0.010, MAT.qinghuaGlaze, 0,  0.095, 0, sideG);
            box(0.095, 0.038, 0.010, MAT.qinghuaGlaze, 0, -0.095, 0, sideG);
            box(0.020, 0.16, 0.010, MAT.whiteGlaze, -0.042, 0, 0, sideG);
            box(0.020, 0.16, 0.010, MAT.whiteGlaze,  0.042, 0, 0, sideG);
            bodyG.add(sideG);
          }
          const lidG = new THREE.Group(); lidG.name = 'Brass_Crown_Lid';
          cyl(0.088, R + 0.010, 0.032, 6, MAT.walnutDark, 0, 0.356, 0, lidG);
          cyl(0.012, 0.082, 0.035, 6, MAT.brass, 0, 0.388, 0, lidG);
          const topPearl = new THREE.Mesh(new THREE.SphereGeometry(0.014, 16, 16), MAT.jade); topPearl.position.y = 0.412; lidG.add(topPearl);
          root.add(lidG);
          root.userData.interact = t => { root.rotation.y = t * 0.4; };
          return root;
        },
  DIY_F05: () => {
          const root = new THREE.Group(); root.name = 'DIY_F05_revolving_papercut_lantern';
          const R = 0.155, yBot = 0.075, yTop = 0.42;
          cyl(R + 0.02, R + 0.03, 0.035, 8, MAT.walnutDark, 0, 0.018, 0, root);
          cyl(R + 0.008, R + 0.016, 0.038, 8, MAT.walnut, 0, 0.055, 0, root);
          cyl(R + 0.025, R + 0.012, 0.032, 8, MAT.walnut, 0, yTop, 0, root);
          cyl(0.032, R + 0.035, 0.095, 8, MAT.walnutDark, 0, yTop + 0.062, 0, root);
          const topFinial = new THREE.Mesh(new THREE.SphereGeometry(0.022, 16, 16), MAT.brass); topFinial.position.y = 0.54; root.add(topFinial);
          for (let i = 0; i < 8; i++) {
            const ang = (i / 8) * Math.PI * 2;
            cyl(0.009, 0.009, yTop - yBot, 12, MAT.walnut, Math.cos(ang) * R, (yTop + yBot) / 2, Math.sin(ang) * R, root);
          }
          cyl(0.005, 0.005, 0.44, 16, MAT.brass, 0, 0.28, 0, root);
          cyl(0.038, 0.042, 0.12, 20, MAT.glowCore, 0, 0.14, 0, root, 'Candle_Light_Source');
          const cageG = new THREE.Group(); cageG.name = 'Revolving_Papercut_Cage'; cageG.position.set(0, 0.24, 0);
          const cageR = 0.105, cageH = 0.24;
          [-cageH / 2, cageH / 2].forEach(cy => {
            const ring = new THREE.Mesh(new THREE.TorusGeometry(cageR, 0.005, 10, 32), MAT.papercutRed);
            ring.rotation.x = Math.PI / 2; ring.position.y = cy; cageG.add(ring);
            box(cageR * 2, 0.004, 0.006, MAT.brass, 0, cy, 0, cageG);
            box(0.006, 0.004, cageR * 2, MAT.brass, 0, cy, 0, cageG);
          });
          for (let i = 0; i < 8; i++) {
            const a = (i / 8) * Math.PI * 2;
            const pG = new THREE.Group();
            pG.position.set(Math.cos(a) * cageR, 0, Math.sin(a) * cageR);
            pG.rotation.y = -a + Math.PI / 2;
            box(0.076, 0.022, 0.003, MAT.papercutRed, 0,  0.10, 0, pG);
            box(0.076, 0.022, 0.003, MAT.papercutRed, 0, -0.10, 0, pG);
            box(0.012, cageH, 0.003, MAT.papercutRed, -0.034, 0, 0, pG);
            box(0.012, cageH, 0.003, MAT.papercutRed,  0.034, 0, 0, pG);
            cyl(0.028, 0.028, 0.004, 16, MAT.papercutRed, 0, 0, 0, pG).rotation.x = Math.PI / 2;
            cageG.add(pG);
          }
          const pinwheel = new THREE.Group(); pinwheel.name = 'Thermal_Pinwheel_Top'; pinwheel.position.y = cageH / 2 + 0.018;
          for (let i = 0; i < 8; i++) {
            const va = (i / 8) * Math.PI * 2;
            const vane = box(0.085, 0.003, 0.024, MAT.papercutRed, Math.cos(va) * 0.048, 0, Math.sin(va) * 0.048, pinwheel);
            vane.rotation.y = -va; vane.rotation.x = 0.45;
          }
          cageG.add(pinwheel); root.add(cageG);
          root.userData.interact = t => { cageG.rotation.y = t * 1.4; };
          return root;
        },
};
