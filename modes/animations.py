"""
animations.py — Mode-specific live canvas animations
=====================================================
4 animations, each teaching a different ADC concept visually:

1. standard_animation   — sampling + quantization step by step
2. aliasing_animation   — alias wave building up from undersampling
3. oversampling_animation — 1x vs Mx side-by-side staircase smoothing
4. dithering_animation  — dither noise added before quantization snap
"""

import streamlit as st
import streamlit.components.v1 as components


# ── Shared CSS / style injected into every animation ──────────────────────────
_BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:monospace;background:#0f1117;color:#fafafa;padding:10px}
canvas{display:block;width:100%;background:#0a0a0f}
.screen{border:1px solid #2a2a3a;border-radius:8px;margin-bottom:10px;overflow:hidden}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px;align-items:flex-end}
.ctrl-grp{display:flex;flex-direction:column;gap:3px;flex:1;min-width:120px}
.ctrl-grp label{font-size:10px;color:#666;letter-spacing:.04em;text-transform:uppercase}
.ctrl-grp input[type=range]{width:100%;accent-color:#378ADD}
.val-lbl{font-size:11px;color:#aaa}
.btn-row{display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap}
button{background:#1a1a2a;color:#fafafa;border:1px solid #333;border-radius:6px;
       padding:5px 12px;font-size:11px;font-family:monospace;cursor:pointer}
button:hover{background:#2a2a3a}
button.active{background:#378ADD;border-color:#378ADD;color:#fff}
.info-row{display:grid;gap:6px;margin-bottom:8px}
.info-card{background:#1a1a2a;border-radius:6px;padding:7px 10px;border:1px solid #2a2a3a}
.info-card .lbl{font-size:9px;color:#555;margin-bottom:2px;letter-spacing:.05em;text-transform:uppercase}
.info-card .val{font-size:12px;font-weight:600;font-family:monospace}
.log{background:#0a0a0f;border:1px solid #1a1a2a;border-radius:6px;
     padding:7px 10px;font-size:11px;color:#888;font-family:monospace;min-height:32px;line-height:1.5}
"""


# ─────────────────────────────────────────────────────────────────────────────
# 1.  STANDARD ADC ANIMATION
# ─────────────────────────────────────────────────────────────────────────────
STANDARD_ANIM = f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}
.info-row{{grid-template-columns:repeat(4,1fr)}}
</style></head><body>
<div class="screen"><canvas id="c" height="260"></canvas></div>
<div class="info-row">
  <div class="info-card"><div class="lbl">Sample #</div><div class="val" id="si" style="color:#1D9E75">—</div></div>
  <div class="info-card"><div class="lbl">Analog value</div><div class="val" id="av" style="color:#378ADD">—</div></div>
  <div class="info-card"><div class="lbl">Quantized</div><div class="val" id="qv" style="color:#D85A30">—</div></div>
  <div class="info-card"><div class="lbl">Error</div><div class="val" id="ev" style="color:#BA7517">—</div></div>
</div>
<div class="controls">
  <div class="ctrl-grp"><label>Signal Freq (Hz)</label>
    <input type="range" id="freq" min="1" max="20" value="4" step="1">
    <span class="val-lbl" id="freq-v">4 Hz</span></div>
  <div class="ctrl-grp"><label>Sample Rate (Hz)</label>
    <input type="range" id="sr" min="5" max="80" value="40" step="1">
    <span class="val-lbl" id="sr-v">40 Hz</span></div>
  <div class="ctrl-grp"><label>ADC Bits</label>
    <input type="range" id="bits" min="1" max="8" value="3" step="1">
    <span class="val-lbl" id="bits-v">3 bits = 8 levels</span></div>
  <div class="ctrl-grp"><label>Speed</label>
    <input type="range" id="spd" min="1" max="10" value="4" step="1">
    <span class="val-lbl" id="spd-v">medium</span></div>
</div>
<div class="btn-row">
  <button id="btnPlay" class="active">⏸ Pause</button>
  <button id="btnStep">Step once</button>
  <button id="btnReset">Reset</button>
  <button id="btnLow" style="border-color:#E24B4A;color:#E24B4A">2-bit demo</button>
</div>
<div class="log" id="log">ADC sampling — watch each sample being taken and quantized in real time</div>
<script>
const cv=document.getElementById('c'),ctx=cv.getContext('2d');
function resize(){{const r=cv.parentElement.getBoundingClientRect();cv.width=r.width||800;}}
resize();new ResizeObserver(resize).observe(cv.parentElement);
let freq=4,sr=40,bits=3,speed=4,playing=true,sampleIdx=0,samples=[],lastTime=0,accumMs=0;
const C={{bg:'#0a0a0f',grid:'#1a1a2a',analog:'#378ADD',cursor:'#FAC775',dot:'#1D9E75',
          stem:'#1D9E75',quant:'#D85A30',level:'rgba(216,90,48,0.10)',error:'#BA7517',text:'#444'}};
function getLevels(b){{const n=2**b,a=[];for(let i=0;i<=n;i++)a.push(-1+2*i/n);return a;}}
function quantize(v,b){{const n=2**b,step=2/n,idx=Math.max(0,Math.min(n,Math.floor((v+1)/step+0.5)));return -1+idx*step;}}
function analog(t){{return Math.sin(2*Math.PI*freq*t);}}
function draw(){{
  const w=cv.width,h=cv.height,pad={{l:52,r:16,t:20,b:30}};
  const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b,dur=2.0;
  const tx=t=>pad.l+(t/dur)*pw,vy=v=>pad.t+ph/2-v*(ph/2.3);
  ctx.clearRect(0,0,w,h);ctx.fillStyle=C.bg;ctx.fillRect(0,0,w,h);
  const levels=getLevels(bits);
  ctx.strokeStyle=C.level;ctx.lineWidth=0.5;ctx.setLineDash([3,6]);
  levels.forEach(lv=>{{ctx.beginPath();ctx.moveTo(pad.l,vy(lv));ctx.lineTo(pad.l+pw,vy(lv));ctx.stroke();
    ctx.fillStyle='#3a3a4a';ctx.font='9px monospace';ctx.textAlign='right';
    ctx.fillText(lv.toFixed(2),pad.l-4,vy(lv)+3);}});
  ctx.setLineDash([]);
  ctx.strokeStyle='#1a1a2a';ctx.lineWidth=0.5;
  for(let g=0;g<=10;g++){{const x=pad.l+(g/10)*pw;ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,pad.t+ph);ctx.stroke();
    ctx.fillStyle=C.text;ctx.font='9px monospace';ctx.textAlign='center';ctx.fillText((g*dur/10).toFixed(1)+'s',x,pad.t+ph+16);}}
  ctx.strokeStyle=C.analog;ctx.lineWidth=2;ctx.beginPath();
  for(let i=0;i<=pw*2;i++){{const t=(i/(pw*2))*dur;i===0?ctx.moveTo(tx(t),vy(analog(t))):ctx.lineTo(tx(t),vy(analog(t)));}}
  ctx.stroke();
  samples.forEach((s,idx)=>{{
    const x=tx(s.t),ya=vy(s.analog),yq=vy(s.quant),last=idx===samples.length-1;
    ctx.strokeStyle=last?C.stem:'rgba(29,158,117,0.25)';ctx.lineWidth=last?1.5:0.8;ctx.setLineDash(last?[]:[2,4]);
    ctx.beginPath();ctx.moveTo(x,vy(0));ctx.lineTo(x,ya);ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle=last?C.dot:'rgba(29,158,117,0.4)';ctx.beginPath();ctx.arc(x,ya,last?5:2.5,0,Math.PI*2);ctx.fill();
    if(last){{
      ctx.strokeStyle='rgba(216,90,48,0.5)';ctx.lineWidth=1;ctx.setLineDash([3,3]);
      ctx.beginPath();ctx.moveTo(x,ya);ctx.lineTo(x,yq);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle=C.quant;ctx.beginPath();ctx.arc(x,yq,6,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle=C.cursor;ctx.lineWidth=1;ctx.setLineDash([4,3]);
      ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,pad.t+ph);ctx.stroke();ctx.setLineDash([]);
    }}
  }});
  if(samples.length>1){{
    ctx.strokeStyle=C.quant;ctx.lineWidth=2;ctx.beginPath();
    samples.forEach((s,i)=>{{const x=tx(s.t),y=vy(s.quant);
      if(i===0)ctx.moveTo(x,y);else{{ctx.lineTo(tx(samples[i-1].t),vy(samples[i-1].quant));ctx.lineTo(x,y);}}}});
    ctx.stroke();
  }}
}}
function addSample(){{
  const t=sampleIdx/sr;if(t>2.0){{sampleIdx=0;samples=[];}}
  const av=analog(t),qv=quantize(av,bits);
  samples.push({{t,analog:av,quant:qv}});if(samples.length>120)samples.shift();
  document.getElementById('si').textContent=sampleIdx;
  document.getElementById('av').textContent=av.toFixed(4);
  document.getElementById('qv').textContent=qv.toFixed(4);
  document.getElementById('ev').textContent=(qv-av).toFixed(4);
  const step=(2/2**bits).toFixed(4);
  document.getElementById('log').innerHTML=
    '<span style="color:#1D9E75">t='+t.toFixed(4)+'s</span>  analog=<span style="color:#378ADD">'+av.toFixed(4)+'</span>'
    +'  snap→<span style="color:#D85A30">'+qv.toFixed(4)+'</span>'
    +'  error=<span style="color:#BA7517">'+(qv-av).toFixed(4)+'</span>'
    +'  <span style="color:#444">[step='+step+', levels='+2**bits+']</span>';
  sampleIdx++;
}}
const msPerSample=()=>1000/(sr*speed/4);
function loop(ts){{
  requestAnimationFrame(loop);
  if(!playing){{draw();return;}}
  const dt=ts-lastTime;lastTime=ts;accumMs+=dt;
  const iv=msPerSample();while(accumMs>=iv){{addSample();accumMs-=iv;}}
  draw();
}}
document.getElementById('freq').oninput=e=>{{freq=+e.target.value;document.getElementById('freq-v').textContent=freq+' Hz';sampleIdx=0;samples=[];}};
document.getElementById('sr').oninput=e=>{{sr=+e.target.value;document.getElementById('sr-v').textContent=sr+' Hz';sampleIdx=0;samples=[];}};
document.getElementById('bits').oninput=e=>{{bits=+e.target.value;document.getElementById('bits-v').textContent=bits+' bits = '+2**bits+' levels';sampleIdx=0;samples=[];}};
document.getElementById('spd').oninput=e=>{{speed=+e.target.value;const n=['','very slow','slow','med-slow','medium','med-fast','fast','faster','very fast','ultra','max'];document.getElementById('spd-v').textContent=n[speed]||speed;}};
document.getElementById('btnPlay').onclick=function(){{playing=!playing;this.textContent=playing?'⏸ Pause':'▶ Play';this.classList.toggle('active',playing);if(playing){{lastTime=performance.now();accumMs=0;}}}};
document.getElementById('btnStep').onclick=()=>{{playing=false;document.getElementById('btnPlay').textContent='▶ Play';document.getElementById('btnPlay').classList.remove('active');addSample();draw();}};
document.getElementById('btnReset').onclick=()=>{{sampleIdx=0;samples=[];draw();}};
document.getElementById('btnLow').onclick=()=>{{bits=2;freq=3;document.getElementById('bits').value=2;document.getElementById('freq').value=3;document.getElementById('bits-v').textContent='2 bits = 4 levels';document.getElementById('freq-v').textContent='3 Hz';sampleIdx=0;samples=[];}};
lastTime=performance.now();requestAnimationFrame(loop);
</script></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# 2.  ALIASING ANIMATION
# ─────────────────────────────────────────────────────────────────────────────
ALIASING_ANIM = f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}
.info-row{{grid-template-columns:repeat(4,1fr)}}
</style></head><body>
<div class="screen"><canvas id="c" height="280"></canvas></div>
<div class="info-row">
  <div class="info-card"><div class="lbl">Signal freq</div><div class="val" id="sf" style="color:#378ADD">—</div></div>
  <div class="info-card"><div class="lbl">Sample rate</div><div class="val" id="sr2" style="color:#1D9E75">—</div></div>
  <div class="info-card"><div class="lbl">Nyquist limit</div><div class="val" id="nq" style="color:#FAC775">—</div></div>
  <div class="info-card"><div class="lbl">Alias freq</div><div class="val" id="af" style="color:#E24B4A">—</div></div>
</div>
<div class="controls">
  <div class="ctrl-grp"><label>Signal Freq (Hz)</label>
    <input type="range" id="freq" min="1" max="30" value="6" step="1">
    <span class="val-lbl" id="freq-v">6 Hz</span></div>
  <div class="ctrl-grp"><label>Sample Rate (Hz)</label>
    <input type="range" id="sr" min="4" max="40" value="10" step="1">
    <span class="val-lbl" id="sr-v">10 Hz</span></div>
  <div class="ctrl-grp"><label>Speed</label>
    <input type="range" id="spd" min="1" max="8" value="3" step="1">
    <span class="val-lbl" id="spd-v">slow</span></div>
</div>
<div class="btn-row">
  <button id="btnPlay" class="active">⏸ Pause</button>
  <button id="btnReset">Reset</button>
  <button id="btnAlias" style="border-color:#E24B4A;color:#E24B4A">Demo aliasing</button>
  <button id="btnSafe"  style="border-color:#1D9E75;color:#1D9E75">Safe sampling</button>
</div>
<div class="log" id="log">Move the Signal Freq slider above the Nyquist limit to see aliasing appear</div>
<script>
const cv=document.getElementById('c'),ctx=cv.getContext('2d');
function resize(){{const r=cv.parentElement.getBoundingClientRect();cv.width=r.width||800;}}
resize();new ResizeObserver(resize).observe(cv.parentElement);
let freq=6,sr=10,speed=3,playing=true,sampleIdx=0,samples=[],lastTime=0,accumMs=0;
function analog(t){{return Math.sin(2*Math.PI*freq*t);}}
function aliasFn(t,af){{return Math.sin(2*Math.PI*af*t);}}
function computeAlias(){{const fm=freq%sr;return fm<=sr/2?fm:sr-fm;}}
function draw(){{
  const w=cv.width,h=cv.height,pad={{l:12,r:12,t:20,b:28}};
  const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b,dur=2.0;
  const tx=t=>pad.l+(t/dur)*pw,vy=v=>pad.t+ph/2-v*(ph/2.4);
  const aliased=freq>sr/2,af=computeAlias();
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#0a0a0f';ctx.fillRect(0,0,w,h);
  // grid
  ctx.strokeStyle='#1a1a2a';ctx.lineWidth=0.5;
  for(let g=0;g<=10;g++){{const x=pad.l+(g/10)*pw;ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,pad.t+ph);ctx.stroke();
    ctx.fillStyle='#444';ctx.font='9px monospace';ctx.textAlign='center';ctx.fillText((g*dur/10).toFixed(1)+'s',x,pad.t+ph+16);}}
  ctx.beginPath();ctx.moveTo(pad.l,vy(0));ctx.lineTo(pad.l+pw,vy(0));ctx.strokeStyle='#2a2a2a';ctx.lineWidth=0.5;ctx.stroke();
  // true signal
  ctx.strokeStyle='#378ADD';ctx.lineWidth=2;ctx.beginPath();
  for(let i=0;i<=pw*2;i++){{const t=(i/(pw*2))*dur;i===0?ctx.moveTo(tx(t),vy(analog(t))):ctx.lineTo(tx(t),vy(analog(t)));}}
  ctx.stroke();
  // alias wave (builds up from samples)
  if(aliased&&samples.length>2){{
    ctx.strokeStyle='rgba(226,75,74,0.35)';ctx.lineWidth=2;ctx.setLineDash([5,4]);ctx.beginPath();
    for(let i=0;i<=pw*2;i++){{const t=(i/(pw*2))*dur;i===0?ctx.moveTo(tx(t),vy(aliasFn(t,af))):ctx.lineTo(tx(t),vy(aliasFn(t,af)));}}
    ctx.stroke();ctx.setLineDash([]);
  }}
  // samples
  samples.forEach((s,idx)=>{{
    const x=tx(s.t),ya=vy(s.v),last=idx===samples.length-1;
    ctx.strokeStyle=last?(aliased?'#E24B4A':'#1D9E75'):'rgba(29,158,117,0.3)';
    ctx.lineWidth=last?1.5:0.8;ctx.setLineDash(last?[]:[2,4]);
    ctx.beginPath();ctx.moveTo(x,vy(0));ctx.lineTo(x,ya);ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle=last?(aliased?'#E24B4A':'#1D9E75'):(aliased?'rgba(226,75,74,0.4)':'rgba(29,158,117,0.4)');
    ctx.beginPath();ctx.arc(x,ya,last?5:3,0,Math.PI*2);ctx.fill();
  }});
  // legend
  ctx.fillStyle='#378ADD';ctx.font='10px monospace';ctx.textAlign='left';ctx.fillText('— true signal ('+freq+' Hz)',pad.l+4,pad.t+14);
  if(aliased){{ctx.fillStyle='rgba(226,75,74,0.8)';ctx.fillText('- - alias ('+af+' Hz)',pad.l+4,pad.t+28);}}
  if(aliased){{
    ctx.fillStyle='rgba(226,75,74,0.15)';ctx.fillRect(0,0,w,h);
    ctx.fillStyle='#E24B4A';ctx.font='bold 11px monospace';ctx.textAlign='center';
    ctx.fillText('⚠ ALIASING: '+freq+' Hz > Nyquist '+sr/2+' Hz → appears as '+af+' Hz',w/2,pad.t+h-pad.b-2);
  }}
}}
function addSample(){{
  const t=sampleIdx/sr;if(t>2.0){{sampleIdx=0;samples=[];}}
  samples.push({{t,v:analog(t)}});if(samples.length>80)samples.shift();
  const aliased=freq>sr/2,af=computeAlias();
  document.getElementById('sf').textContent=freq+' Hz';
  document.getElementById('sr2').textContent=sr+' Hz';
  document.getElementById('nq').textContent=(sr/2)+' Hz';
  document.getElementById('af').style.color=aliased?'#E24B4A':'#1D9E75';
  document.getElementById('af').textContent=aliased?(af+' Hz ⚠'):'none ✓';
  document.getElementById('log').innerHTML=aliased
    ?'<span style="color:#E24B4A">ALIASING: signal '+freq+' Hz > Nyquist '+sr/2+' Hz. ADC records it as '+af+' Hz — completely wrong!</span>'
    :'<span style="color:#1D9E75">Safe: signal '+freq+' Hz &lt; Nyquist '+sr/2+' Hz. ADC captures correctly.</span>';
  sampleIdx++;
}}
const msPerSample=()=>1000/(sr*speed/3);
function loop(ts){{
  requestAnimationFrame(loop);
  if(!playing){{draw();return;}}
  const dt=ts-lastTime;lastTime=ts;accumMs+=dt;
  const iv=msPerSample();while(accumMs>=iv){{addSample();accumMs-=iv;}}
  draw();
}}
document.getElementById('freq').oninput=e=>{{freq=+e.target.value;document.getElementById('freq-v').textContent=freq+' Hz';sampleIdx=0;samples=[];}};
document.getElementById('sr').oninput=e=>{{sr=+e.target.value;document.getElementById('sr-v').textContent=sr+' Hz';sampleIdx=0;samples=[];}};
document.getElementById('spd').oninput=e=>{{speed=+e.target.value;const n=['','very slow','slow','medium','fast','faster','very fast','ultra','max'];document.getElementById('spd-v').textContent=n[speed]||speed;}};
document.getElementById('btnPlay').onclick=function(){{playing=!playing;this.textContent=playing?'⏸ Pause':'▶ Play';this.classList.toggle('active',playing);if(playing){{lastTime=performance.now();accumMs=0;}}}};
document.getElementById('btnReset').onclick=()=>{{sampleIdx=0;samples=[];}};
document.getElementById('btnAlias').onclick=()=>{{freq=18;sr=10;document.getElementById('freq').value=18;document.getElementById('sr').value=10;document.getElementById('freq-v').textContent='18 Hz';document.getElementById('sr-v').textContent='10 Hz';sampleIdx=0;samples=[];}};
document.getElementById('btnSafe').onclick=()=>{{freq=4;sr=10;document.getElementById('freq').value=4;document.getElementById('sr').value=10;document.getElementById('freq-v').textContent='4 Hz';document.getElementById('sr-v').textContent='10 Hz';sampleIdx=0;samples=[];}};
lastTime=performance.now();requestAnimationFrame(loop);
</script></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# 3.  OVERSAMPLING ANIMATION
# ─────────────────────────────────────────────────────────────────────────────
OVERSAMPLING_ANIM = f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}
.info-row{{grid-template-columns:repeat(4,1fr)}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
</style></head><body>
<div class="two-col">
  <div><div style="font-size:10px;color:#D85A30;margin-bottom:4px;font-family:monospace;text-transform:uppercase">Normal (1×) — coarse staircase</div>
    <div class="screen"><canvas id="c1" height="200"></canvas></div></div>
  <div><div style="font-size:10px;color:#1D9E75;margin-bottom:4px;font-family:monospace;text-transform:uppercase" id="osr-label">Oversampled (4×) — smoother</div>
    <div class="screen"><canvas id="c2" height="200"></canvas></div></div>
</div>
<div class="info-row">
  <div class="info-card"><div class="lbl">Normal SNR</div><div class="val" id="snr1" style="color:#D85A30">—</div></div>
  <div class="info-card"><div class="lbl">Oversamp SNR</div><div class="val" id="snr2" style="color:#1D9E75">—</div></div>
  <div class="info-card"><div class="lbl">SNR gain</div><div class="val" id="gain" style="color:#FAC775">—</div></div>
  <div class="info-card"><div class="lbl">Theory</div><div class="val" id="theo" style="color:#9FE1CB">—</div></div>
</div>
<div class="controls">
  <div class="ctrl-grp"><label>Signal Freq (Hz)</label>
    <input type="range" id="freq" min="1" max="15" value="4" step="1">
    <span class="val-lbl" id="freq-v">4 Hz</span></div>
  <div class="ctrl-grp"><label>ADC Bits</label>
    <input type="range" id="bits" min="2" max="6" value="3" step="1">
    <span class="val-lbl" id="bits-v">3 bits</span></div>
  <div class="ctrl-grp"><label>Oversample Factor M</label>
    <input type="range" id="osr" min="1" max="16" value="4" step="1">
    <span class="val-lbl" id="osr-v">4×</span></div>
  <div class="ctrl-grp"><label>Speed</label>
    <input type="range" id="spd" min="1" max="8" value="4" step="1">
    <span class="val-lbl" id="spd-v">medium</span></div>
</div>
<div class="btn-row">
  <button id="btnPlay" class="active">⏸ Pause</button>
  <button id="btnReset">Reset</button>
  <button id="btn1" style="border-color:#D85A30;color:#D85A30">M=1 (none)</button>
  <button id="btn4">M=4</button>
  <button id="btn16" style="border-color:#1D9E75;color:#1D9E75">M=16</button>
</div>
<div class="log" id="log">Increase M to watch the right staircase smooth out — same ADC, less noise</div>
<script>
const c1=document.getElementById('c1'),x1=c1.getContext('2d');
const c2=document.getElementById('c2'),x2=c2.getContext('2d');
function resize(){{
  const r1=c1.parentElement.getBoundingClientRect();c1.width=r1.width||380;
  const r2=c2.parentElement.getBoundingClientRect();c2.width=r2.width||380;
}}
resize();new ResizeObserver(resize).observe(c1.parentElement);new ResizeObserver(resize).observe(c2.parentElement);
let freq=4,bits=3,osr=4,speed=4,playing=true,sampleIdx=0,samples1=[],samples2=[],lastTime=0,accumMs=0;
function analog(t){{return Math.sin(2*Math.PI*freq*t);}}
function quantize(v,b){{const n=2**b,step=2/n,idx=Math.max(0,Math.min(n,Math.floor((v+1)/step+0.5)));return -1+idx*step;}}
function computeSNR(samps){{
  if(samps.length<4)return 0;
  const sig=samps.map(s=>s.analog),quant=samps.map(s=>s.quant);
  const sp=sig.reduce((a,v)=>a+v*v,0)/sig.length;
  const np=sig.map((v,i)=>v-quant[i]).reduce((a,v)=>a+v*v,0)/sig.length;
  return np===0?99:10*Math.log10(sp/np);
}}
function theorySNR(){{ return 6.02*bits+1.76; }}
function theoryOSR(){{ return osr>1 ? theorySNR()+10*Math.log10(osr) : theorySNR(); }}
function drawCanvas(ctx,samples,color,label){{
  const w=ctx.canvas.width,h=ctx.canvas.height,pad={{l:36,r:8,t:12,b:20}};
  const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b,dur=2.0;
  const tx=t=>pad.l+(t/dur)*pw,vy=v=>pad.t+ph/2-v*(ph/2.4);
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#0a0a0f';ctx.fillRect(0,0,w,h);
  ctx.strokeStyle='#1a1a2a';ctx.lineWidth=0.5;
  for(let g=0;g<=8;g++){{const x=pad.l+(g/8)*pw;ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,pad.t+ph);ctx.stroke();}}
  const n=2**bits,step=2/n;
  ctx.strokeStyle='rgba(255,255,255,0.05)';ctx.lineWidth=0.5;ctx.setLineDash([2,6]);
  for(let i=0;i<=n;i++){{const y=vy(-1+i*step);ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(pad.l+pw,y);ctx.stroke();}}
  ctx.setLineDash([]);
  ctx.strokeStyle='#378ADD';ctx.lineWidth=1.5;ctx.beginPath();
  for(let i=0;i<=pw*2;i++){{const t=(i/(pw*2))*dur;i===0?ctx.moveTo(tx(t),vy(analog(t))):ctx.lineTo(tx(t),vy(analog(t)));}}
  ctx.stroke();
  if(samples.length>1){{
    ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();
    samples.forEach((s,i)=>{{const x=tx(s.t),y=vy(s.quant);
      if(i===0)ctx.moveTo(x,y);else{{ctx.lineTo(tx(samples[i-1].t),vy(samples[i-1].quant));ctx.lineTo(x,y);}}}});
    ctx.stroke();
  }}
  if(samples.length>0){{const s=samples[samples.length-1];ctx.fillStyle=color;ctx.beginPath();ctx.arc(tx(s.t),vy(s.quant),5,0,Math.PI*2);ctx.fill();}}
}}
function addSamples(){{
  const baseRate=20;
  const t=sampleIdx/baseRate;
  if(t>2.0){{sampleIdx=0;samples1=[];samples2=[];}}
  const av=analog(t);
  samples1.push({{t,analog:av,quant:quantize(av,bits)}});
  if(samples1.length>100)samples1.shift();
  // oversampled: average osr sub-samples
  let sum=0;for(let k=0;k<osr;k++)sum+=quantize(analog(t+k/(baseRate*osr)),bits);
  const qOver=sum/osr;
  samples2.push({{t,analog:av,quant:qOver}});
  if(samples2.length>100)samples2.shift();
  const snr1=computeSNR(samples1),snr2=computeSNR(samples2);
  const theo=osr>1?10*Math.log10(osr):0;
  const tSNR1=theorySNR(), tSNR2=theoryOSR(), tGain=theo;
  document.getElementById('snr1').textContent=tSNR1.toFixed(1)+' dB';
  document.getElementById('snr2').textContent=tSNR2.toFixed(1)+' dB';
  document.getElementById('gain').textContent=(tGain>=0?'+':'')+tGain.toFixed(1)+' dB';
  document.getElementById('theo').textContent='+'+theo.toFixed(1)+' dB';
  document.getElementById('log').innerHTML=
    'Normal ('+bits+'-bit): <span style="color:#D85A30">'+tSNR1.toFixed(1)+' dB</span>  →  '
    +'Oversampled '+osr+'×: <span style="color:#1D9E75">'+tSNR2.toFixed(1)+' dB</span>  '
    +'<span style="color:#FAC775">gain=+'+tGain.toFixed(1)+' dB</span>  '
    +'<span style="color:#444">(6.02×'+bits+'+1.76 + 10×log₁₀('+osr+')/2)</span>';
  sampleIdx++;
}}
function loop(ts){{
  requestAnimationFrame(loop);
  if(!playing){{drawCanvas(x1,samples1,'#D85A30','Normal');drawCanvas(x2,samples2,'#1D9E75','Over');return;}}
  const dt=ts-lastTime;lastTime=ts;accumMs+=dt;
  const iv=1000/(20*speed/4);while(accumMs>=iv){{addSamples();accumMs-=iv;}}
  drawCanvas(x1,samples1,'#D85A30','Normal');drawCanvas(x2,samples2,'#1D9E75','Over');
}}
function setOSR(v){{osr=v;document.getElementById('osr').value=v;document.getElementById('osr-v').textContent=v+'×';
  document.getElementById('osr-label').textContent='Oversampled ('+v+'×) — '+(v===1?'no improvement':v+'× smoother');
  sampleIdx=0;samples1=[];samples2=[];}}
document.getElementById('freq').oninput=e=>{{freq=+e.target.value;document.getElementById('freq-v').textContent=freq+' Hz';sampleIdx=0;samples1=[];samples2=[];}};
document.getElementById('bits').oninput=e=>{{bits=+e.target.value;document.getElementById('bits-v').textContent=bits+' bits';sampleIdx=0;samples1=[];samples2=[];}};
document.getElementById('osr').oninput=e=>setOSR(+e.target.value);
document.getElementById('spd').oninput=e=>{{speed=+e.target.value;const n=['','very slow','slow','med-slow','medium','med-fast','fast','faster','max'];document.getElementById('spd-v').textContent=n[speed]||speed;}};
document.getElementById('btnPlay').onclick=function(){{playing=!playing;this.textContent=playing?'⏸ Pause':'▶ Play';this.classList.toggle('active',playing);if(playing){{lastTime=performance.now();accumMs=0;}}}};
document.getElementById('btnReset').onclick=()=>{{sampleIdx=0;samples1=[];samples2=[];}};
document.getElementById('btn1').onclick=()=>setOSR(1);
document.getElementById('btn4').onclick=()=>setOSR(4);
document.getElementById('btn16').onclick=()=>setOSR(16);
lastTime=performance.now();requestAnimationFrame(loop);
</script></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# 4.  DITHERING ANIMATION
# ─────────────────────────────────────────────────────────────────────────────
DITHERING_ANIM = f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}
.info-row{{grid-template-columns:repeat(4,1fr)}}
</style></head><body>
<div class="screen"><canvas id="c" height="280"></canvas></div>
<div class="info-row">
  <div class="info-card"><div class="lbl">Analog value</div><div class="val" id="av" style="color:#378ADD">—</div></div>
  <div class="info-card"><div class="lbl">Dither added</div><div class="val" id="dv" style="color:#7F77DD">—</div></div>
  <div class="info-card"><div class="lbl">After dither</div><div class="val" id="da" style="color:#9FE1CB">—</div></div>
  <div class="info-card"><div class="lbl">Quantized</div><div class="val" id="qv" style="color:#D85A30">—</div></div>
</div>
<div class="controls">
  <div class="ctrl-grp"><label>Signal Freq (Hz)</label>
    <input type="range" id="freq" min="1" max="15" value="3" step="1">
    <span class="val-lbl" id="freq-v">3 Hz</span></div>
  <div class="ctrl-grp"><label>ADC Bits (low = visible)</label>
    <input type="range" id="bits" min="1" max="5" value="2" step="1">
    <span class="val-lbl" id="bits-v">2 bits = 4 levels</span></div>
  <div class="ctrl-grp"><label>Amplitude (low = visible)</label>
    <input type="range" id="amp" min="0.1" max="1.0" value="0.35" step="0.05">
    <span class="val-lbl" id="amp-v">0.35</span></div>
  <div class="ctrl-grp"><label>Speed</label>
    <input type="range" id="spd" min="1" max="8" value="2" step="1">
    <span class="val-lbl" id="spd-v">slow</span></div>
</div>
<div class="btn-row">
  <button id="btnPlay" class="active">⏸ Pause</button>
  <button id="btnStep">Step once</button>
  <button id="btnReset">Reset</button>
  <button id="btnDither" class="active">Dithering ON</button>
</div>
<div class="log" id="log">Watch the purple dot jitter slightly before snapping to the nearest level</div>
<script>
const cv=document.getElementById('c'),ctx=cv.getContext('2d');
function resize(){{const r=cv.parentElement.getBoundingClientRect();cv.width=r.width||800;}}
resize();new ResizeObserver(resize).observe(cv.parentElement);
let freq=3,bits=2,amp=0.35,speed=2,playing=true,useDither=true;
let sampleIdx=0,samples=[],lastTime=0,accumMs=0,flashDither=null,flashT=0;
function analog(t){{return amp*Math.sin(2*Math.PI*freq*t);}}
function quantize(v,b){{const n=2**b,step=2/n,idx=Math.max(0,Math.min(n,Math.floor((v+1)/step+0.5)));return -1+idx*step;}}
function tpdf(step){{return (Math.random()-0.5)*step+(Math.random()-0.5)*step;}}
function draw(){{
  const w=cv.width,h=cv.height;
  const pl=52,pr=16,pt=20,pb=30,pw=w-pl-pr,ph=h-pt-pb,dur=2.0;
  const tx=t=>pl+(t/dur)*pw,vy=v=>pt+ph/2-v*(ph/2.4);
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#0a0a0f';ctx.fillRect(0,0,w,h);
  const n=2**bits,step=2/n;
  // level lines
  ctx.strokeStyle='rgba(216,90,48,0.15)';ctx.lineWidth=0.7;ctx.setLineDash([4,6]);
  for(let i=0;i<=n;i++){{const y=vy(-1+i*step);ctx.beginPath();ctx.moveTo(pl,y);ctx.lineTo(pl+pw,y);ctx.stroke();
    ctx.fillStyle='#3a3a4a';ctx.font='9px monospace';ctx.textAlign='right';ctx.fillText((-1+i*step).toFixed(2),pl-4,y+3);}}
  ctx.setLineDash([]);
  // grid
  ctx.strokeStyle='#1a1a2a';ctx.lineWidth=0.5;
  for(let g=0;g<=10;g++){{const x=pl+(g/10)*pw;ctx.beginPath();ctx.moveTo(x,pt);ctx.lineTo(x,pt+ph);ctx.stroke();
    ctx.fillStyle='#444';ctx.font='9px monospace';ctx.textAlign='center';ctx.fillText((g*dur/10).toFixed(1)+'s',x,pt+ph+16);}}
  // analog
  ctx.strokeStyle='#378ADD';ctx.lineWidth=2;ctx.beginPath();
  for(let i=0;i<=pw*2;i++){{const t=(i/(pw*2))*dur;i===0?ctx.moveTo(tx(t),vy(analog(t))):ctx.lineTo(tx(t),vy(analog(t)));}}
  ctx.stroke();
  // past samples
  if(samples.length>1){{
    ctx.strokeStyle='rgba(216,90,48,0.6)';ctx.lineWidth=1.5;ctx.beginPath();
    samples.forEach((s,i)=>{{const x=tx(s.t),y=vy(s.quant);
      if(i===0)ctx.moveTo(x,y);else{{ctx.lineTo(tx(samples[i-1].t),vy(samples[i-1].quant));ctx.lineTo(x,y);}}}});
    ctx.stroke();
  }}
  samples.forEach(s=>{{
    ctx.fillStyle='rgba(216,90,48,0.5)';ctx.beginPath();ctx.arc(tx(s.t),vy(s.quant),3,0,Math.PI*2);ctx.fill();}});
  // flash dither moment
  if(flashDither&&Date.now()-flashT<600){{
    const s=flashDither,x=tx(s.t);
    // analog point
    ctx.fillStyle='#378ADD';ctx.beginPath();ctx.arc(x,vy(s.analog),6,0,Math.PI*2);ctx.fill();
    if(useDither){{
      // dither offset arrow
      ctx.strokeStyle='#7F77DD';ctx.lineWidth=2;
      ctx.beginPath();ctx.moveTo(x,vy(s.analog));ctx.lineTo(x,vy(s.afterDither));ctx.stroke();
      // after dither point
      ctx.fillStyle='#9FE1CB';ctx.beginPath();ctx.arc(x,vy(s.afterDither),6,0,Math.PI*2);ctx.fill();
      // snap line
      ctx.strokeStyle='rgba(216,90,48,0.6)';ctx.lineWidth=1.5;ctx.setLineDash([3,3]);
      ctx.beginPath();ctx.moveTo(x,vy(s.afterDither));ctx.lineTo(x,vy(s.quant));ctx.stroke();ctx.setLineDash([]);
    }} else {{
      ctx.strokeStyle='rgba(216,90,48,0.6)';ctx.lineWidth=1.5;ctx.setLineDash([3,3]);
      ctx.beginPath();ctx.moveTo(x,vy(s.analog));ctx.lineTo(x,vy(s.quant));ctx.stroke();ctx.setLineDash([]);
    }}
    ctx.fillStyle='#D85A30';ctx.beginPath();ctx.arc(x,vy(s.quant),7,0,Math.PI*2);ctx.fill();
    // cursor
    ctx.strokeStyle='#FAC775';ctx.lineWidth=1;ctx.setLineDash([4,3]);
    ctx.beginPath();ctx.moveTo(x,pt);ctx.lineTo(x,pt+ph);ctx.stroke();ctx.setLineDash([]);
  }}
  // legend
  ctx.fillStyle='#378ADD';ctx.font='10px monospace';ctx.textAlign='left';ctx.fillText('— analog',pl+4,pt+14);
  if(useDither){{ctx.fillStyle='#9FE1CB';ctx.fillText('● after dither',pl+4,pt+28);}}
  ctx.fillStyle='#D85A30';ctx.fillText('● quantized',pl+4,pt+(useDither?42:28));
  ctx.fillStyle=useDither?'#1D9E75':'#E24B4A';ctx.font='bold 10px monospace';ctx.textAlign='right';
  ctx.fillText(useDither?'DITHER ON':'DITHER OFF',pl+pw,pt+14);
}}
function addSample(){{
  const t=sampleIdx/20;if(t>2.0){{sampleIdx=0;samples=[];}}
  const av=analog(t),step=2/2**bits;
  const dv=useDither?tpdf(step):0;
  const ad=av+dv,qv=quantize(ad,bits);
  samples.push({{t,analog:av,dither:dv,afterDither:ad,quant:qv}});
  if(samples.length>80)samples.shift();
  flashDither={{t,analog:av,dither:dv,afterDither:ad,quant:qv}};
  flashT=Date.now();
  document.getElementById('av').textContent=av.toFixed(4);
  document.getElementById('dv').textContent=useDither?(dv>=0?'+':'')+dv.toFixed(4):'0 (off)';
  document.getElementById('da').textContent=useDither?ad.toFixed(4):'—';
  document.getElementById('qv').textContent=qv.toFixed(4);
  const nearestLevel=Math.round((av+1)/step)*step-1;
  document.getElementById('log').innerHTML=useDither
    ?'analog=<span style="color:#378ADD">'+av.toFixed(4)+'</span>'
     +' + dither=<span style="color:#7F77DD">'+(dv>=0?'+':'')+dv.toFixed(4)+'</span>'
     +' → <span style="color:#9FE1CB">'+ad.toFixed(4)+'</span>'
     +' snaps to <span style="color:#D85A30">'+qv.toFixed(4)+'</span>'
    :'analog=<span style="color:#378ADD">'+av.toFixed(4)+'</span>'
     +' snaps directly to <span style="color:#D85A30">'+qv.toFixed(4)+'</span>'
     +' <span style="color:#444">[no dither]</span>';
  sampleIdx++;
}}
const msPerSample=()=>1000/(20*speed/4);
function loop(ts){{
  requestAnimationFrame(loop);
  if(!playing){{draw();return;}}
  const dt=ts-lastTime;lastTime=ts;accumMs+=dt;
  const iv=msPerSample();while(accumMs>=iv){{addSample();accumMs-=iv;}}
  draw();
}}
document.getElementById('freq').oninput=e=>{{freq=+e.target.value;document.getElementById('freq-v').textContent=freq+' Hz';sampleIdx=0;samples=[];flashDither=null;}};
document.getElementById('bits').oninput=e=>{{bits=+e.target.value;document.getElementById('bits-v').textContent=bits+' bits = '+2**bits+' levels';sampleIdx=0;samples=[];flashDither=null;}};
document.getElementById('amp').oninput=e=>{{amp=+e.target.value;document.getElementById('amp-v').textContent=amp.toFixed(2);sampleIdx=0;samples=[];flashDither=null;}};
document.getElementById('spd').oninput=e=>{{speed=+e.target.value;const n=['','very slow','slow','med-slow','medium','med-fast','fast','faster','max'];document.getElementById('spd-v').textContent=n[speed]||speed;}};
document.getElementById('btnPlay').onclick=function(){{playing=!playing;this.textContent=playing?'⏸ Pause':'▶ Play';this.classList.toggle('active',playing);if(playing){{lastTime=performance.now();accumMs=0;}}}};
document.getElementById('btnStep').onclick=()=>{{playing=false;document.getElementById('btnPlay').textContent='▶ Play';document.getElementById('btnPlay').classList.remove('active');addSample();draw();}};
document.getElementById('btnReset').onclick=()=>{{sampleIdx=0;samples=[];flashDither=null;}};
document.getElementById('btnDither').onclick=function(){{useDither=!useDither;this.textContent=useDither?'Dithering ON':'Dithering OFF';this.classList.toggle('active',useDither);sampleIdx=0;samples=[];flashDither=null;}};
lastTime=performance.now();requestAnimationFrame(loop);
</script></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Public functions — call these from each mode file
# ─────────────────────────────────────────────────────────────────────────────

def show_standard_animation():
    with st.expander("▶️ Live Animation — watch the ADC sample and quantize in real time"):
        st.caption("Each green dot = sample taken. Orange dot = after quantization. "
                   "Orange staircase = digital output. Use Step to go one sample at a time.")
        components.html(STANDARD_ANIM, height=560, scrolling=False)


def show_aliasing_animation():
    with st.expander("▶️ Live Animation — watch the alias frequency appear in real time"):
        st.caption("Blue = true signal. Red dashed = alias wave building from samples. "
                   "Push Signal Freq above Nyquist limit to trigger aliasing.")
        components.html(ALIASING_ANIM, height=560, scrolling=False)


def show_oversampling_animation():
    with st.expander("▶️ Live Animation — compare normal vs oversampled staircase side by side"):
        st.caption("Left = normal 1× sampling (coarse staircase). "
                   "Right = oversampled M× (smoother). Increase M to see the improvement live.")
        components.html(OVERSAMPLING_ANIM, height=600, scrolling=False)


def show_dithering_animation():
    with st.expander("▶️ Live Animation — watch dither noise being added before quantization"):
        st.caption("Blue dot = analog sample. Purple arrow = dither offset added. "
                   "Teal dot = after dither. Orange = final quantized level. "
                   "Toggle dithering ON/OFF to compare.")
        components.html(DITHERING_ANIM, height=580, scrolling=False)
