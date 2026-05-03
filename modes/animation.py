import streamlit as st
import streamlit.components.v1 as components


ANIMATION_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:monospace;background:#0f1117;color:#fafafa;padding:12px}
.screen{background:#0a0a0f;border:1px solid #2a2a3a;border-radius:8px;margin-bottom:12px;overflow:hidden}
canvas{display:block;width:100%;height:300px}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.ctrl-grp{display:flex;flex-direction:column;gap:4px;flex:1;min-width:130px}
.ctrl-grp label{font-size:11px;color:#888;letter-spacing:.04em}
.ctrl-grp input[type=range]{width:100%;accent-color:#378ADD}
.val-lbl{font-size:11px;color:#aaa}
.btn-row{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
button{background:#1a1a2a;color:#fafafa;border:1px solid #333;border-radius:6px;padding:6px 14px;font-size:12px;font-family:monospace;cursor:pointer}
button:hover{background:#2a2a3a}
button.active{background:#378ADD;border-color:#378ADD}
.info-row{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}
.info-card{background:#1a1a2a;border-radius:6px;padding:8px 10px;border:1px solid #2a2a3a}
.info-card .lbl{font-size:10px;color:#666;margin-bottom:2px}
.info-card .val{font-size:13px;font-weight:500;font-family:monospace}
.log{background:#0a0a0f;border:1px solid #1a1a2a;border-radius:6px;padding:8px 10px;font-size:11px;color:#888;font-family:monospace;min-height:36px}
</style>
</head>
<body>
<div class="screen"><canvas id="c"></canvas></div>

<div class="info-row">
  <div class="info-card"><div class="lbl">sample #</div><div class="val" id="si" style="color:#1D9E75">—</div></div>
  <div class="info-card"><div class="lbl">analog value</div><div class="val" id="av" style="color:#378ADD">—</div></div>
  <div class="info-card"><div class="lbl">quantized</div><div class="val" id="qv" style="color:#D85A30">—</div></div>
  <div class="info-card"><div class="lbl">error</div><div class="val" id="ev" style="color:#BA7517">—</div></div>
</div>

<div class="controls">
  <div class="ctrl-grp">
    <label>SIGNAL FREQ (Hz)</label>
    <input type="range" id="freq" min="1" max="20" value="4" step="1">
    <span class="val-lbl" id="freq-v">4 Hz</span>
  </div>
  <div class="ctrl-grp">
    <label>SAMPLE RATE (Hz)</label>
    <input type="range" id="sr" min="5" max="80" value="20" step="1">
    <span class="val-lbl" id="sr-v">20 Hz</span>
  </div>
  <div class="ctrl-grp">
    <label>ADC BITS</label>
    <input type="range" id="bits" min="1" max="8" value="3" step="1">
    <span class="val-lbl" id="bits-v">3 bits = 8 levels</span>
  </div>
  <div class="ctrl-grp">
    <label>ANIMATION SPEED</label>
    <input type="range" id="spd" min="1" max="10" value="4" step="1">
    <span class="val-lbl" id="spd-v">medium</span>
  </div>
</div>

<div class="btn-row">
  <button id="btnPlay" class="active">&#9646;&#9646; pause</button>
  <button id="btnStep">step once</button>
  <button id="btnReset">reset</button>
  <button id="btnNyq" style="border-color:#E24B4A;color:#E24B4A;margin-left:auto">test aliasing</button>
  <button id="btnLow" style="border-color:#1D9E75;color:#1D9E75">low bits demo</button>
</div>

<div class="log" id="log">ADC sampling simulator — watch each sample get taken and quantized in real time</div>

<script>
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
function resize(){const r=cv.parentElement.getBoundingClientRect();cv.width=r.width||800;cv.height=300;}
resize();
new ResizeObserver(resize).observe(cv.parentElement);

let freq=4,sr=20,bits=3,speed=4,playing=true;
let sampleIdx=0,samples=[],lastTime=0,accumMs=0,rafId=null;

const C={bg:'#0a0a0f',grid:'#1a1a2a',analog:'#378ADD',cursor:'#FAC775',dot:'#1D9E75',stem:'#1D9E75',quant:'#D85A30',level:'rgba(216,90,48,0.12)',error:'#BA7517',alias:'#E24B4A',text:'#555555'};

function getLevels(b){const n=Math.pow(2,b);const a=[];for(let i=0;i<=n;i++)a.push(-1+(2*i/n));return a;}
function quantize(v,b){const n=Math.pow(2,b);const step=2/n;const idx=Math.max(0,Math.min(n,Math.floor((v+1)/step+0.5)));return -1+idx*step;}
function analog(t){return Math.sin(2*Math.PI*freq*t);}

function draw(){
  const w=cv.width,h=cv.height;
  const pad={l:52,r:16,t:24,b:36};
  const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
  const duration=2.0;
  const tx=t=>pad.l+(t/duration)*pw;
  const vy=v=>pad.t+ph/2-(v*ph/2.3);

  ctx.clearRect(0,0,w,h);
  ctx.fillStyle=C.bg;ctx.fillRect(0,0,w,h);

  const levels=getLevels(bits);

  ctx.strokeStyle=C.level;ctx.lineWidth=0.5;ctx.setLineDash([3,6]);
  levels.forEach(lv=>{
    ctx.beginPath();ctx.moveTo(pad.l,vy(lv));ctx.lineTo(pad.l+pw,vy(lv));ctx.stroke();
    ctx.fillStyle='#444';ctx.font='9px monospace';ctx.textAlign='right';
    ctx.fillText(lv.toFixed(2),pad.l-4,vy(lv)+3);
  });
  ctx.setLineDash([]);

  ctx.strokeStyle=C.grid;ctx.lineWidth=0.5;
  for(let g=0;g<=10;g++){
    const x=pad.l+(g/10)*pw;
    ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,pad.t+ph);ctx.stroke();
    ctx.fillStyle=C.text;ctx.font='9px monospace';ctx.textAlign='center';
    ctx.fillText((g*duration/10).toFixed(1)+'s',x,pad.t+ph+16);
  }

  ctx.strokeStyle=C.analog;ctx.lineWidth=2;ctx.beginPath();
  const steps=pw*2;
  for(let i=0;i<=steps;i++){const t=(i/steps)*duration;const x=tx(t),y=vy(analog(t));i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);}
  ctx.stroke();

  const alias=freq>sr/2;

  samples.forEach((s,idx)=>{
    const x=tx(s.t),ya=vy(s.analog),yq=vy(s.quant),isLast=idx===samples.length-1;
    ctx.strokeStyle=isLast?C.stem:'rgba(29,158,117,0.3)';
    ctx.lineWidth=isLast?1.5:0.8;ctx.setLineDash(isLast?[]:[2,4]);
    ctx.beginPath();ctx.moveTo(x,vy(0));ctx.lineTo(x,ya);ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle=isLast?C.dot:'rgba(29,158,117,0.45)';
    ctx.beginPath();ctx.arc(x,ya,isLast?5:2.5,0,Math.PI*2);ctx.fill();
    if(isLast){
      ctx.strokeStyle='rgba(216,90,48,0.6)';ctx.lineWidth=1.2;ctx.setLineDash([3,3]);
      ctx.beginPath();ctx.moveTo(x,ya);ctx.lineTo(x,yq);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle=C.quant;ctx.beginPath();ctx.arc(x,yq,6,0,Math.PI*2);ctx.fill();
      const err=(s.quant-s.analog);
      ctx.fillStyle=C.error;ctx.font='bold 10px monospace';ctx.textAlign='center';
      ctx.fillText('err='+err.toFixed(3),x,yq-(yq>ya?14:-6));
      ctx.strokeStyle=alias?C.alias:C.cursor;ctx.lineWidth=1;ctx.setLineDash([4,3]);
      ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,pad.t+ph);ctx.stroke();ctx.setLineDash([]);
    }
  });

  if(samples.length>1){
    ctx.strokeStyle=C.quant;ctx.lineWidth=2;ctx.beginPath();
    samples.forEach((s,i)=>{
      const x=tx(s.t),y=vy(s.quant);
      if(i===0){ctx.moveTo(x,y);}
      else{ctx.lineTo(tx(samples[i-1].t),vy(samples[i-1].quant));ctx.lineTo(x,y);}
    });
    ctx.stroke();
  }

  ctx.fillStyle='#fafafa';ctx.font='10px monospace';ctx.textAlign='left';
  ctx.fillText('analog',pad.l+4,pad.t+16);
  ctx.fillStyle=C.analog;ctx.fillRect(pad.l+52,pad.t+9,20,2);
  ctx.fillStyle='#fafafa';ctx.fillText('quantized',pad.l+80,pad.t+16);
  ctx.fillStyle=C.quant;ctx.fillRect(pad.l+144,pad.t+9,20,2);

  if(alias){
    ctx.fillStyle=C.alias;ctx.font='bold 11px monospace';ctx.textAlign='right';
    ctx.fillText('ALIASING: '+freq+'Hz > Nyquist '+(sr/2)+'Hz',pad.l+pw,pad.t+16);
  }
  ctx.fillStyle=C.text;ctx.font='9px monospace';ctx.textAlign='right';
  ctx.fillText(bits+'-bit = '+Math.pow(2,bits)+' levels  |  step='+(2/Math.pow(2,bits)).toFixed(4),pad.l+pw,pad.t+ph+16);
}

function addSample(){
  const t=sampleIdx/sr;
  if(t>2.0){sampleIdx=0;samples=[];}
  const av=analog(t),qv=quantize(av,bits);
  samples.push({t,analog:av,quant:qv});
  if(samples.length>100)samples.shift();
  document.getElementById('si').textContent=sampleIdx;
  document.getElementById('av').textContent=av.toFixed(4);
  document.getElementById('qv').textContent=qv.toFixed(4);
  document.getElementById('ev').textContent=(qv-av).toFixed(4);
  const alias=freq>sr/2;
  const step=(2/Math.pow(2,bits)).toFixed(4);
  const log=document.getElementById('log');
  if(alias){
    log.innerHTML='<span style="color:#E24B4A">ALIASING: signal '+freq+'Hz exceeds Nyquist '+(sr/2)+'Hz — alias appears at '+Math.abs(freq-sr)+'Hz</span>';
  } else {
    log.innerHTML='<span style="color:#1D9E75">t='+t.toFixed(4)+'s</span>  analog=<span style="color:#378ADD">'+av.toFixed(4)+'</span>  →  snap to level=<span style="color:#D85A30">'+qv.toFixed(4)+'</span>  error=<span style="color:#BA7517">'+((qv-av).toFixed(4))+'</span>  [step='+step+']';
  }
  sampleIdx++;
}

const msPerSample=()=>1000/(sr*speed/4);
function loop(ts){
  rafId=requestAnimationFrame(loop);
  if(!playing){draw();return;}
  const dt=ts-lastTime;lastTime=ts;accumMs+=dt;
  const interval=msPerSample();
  while(accumMs>=interval){addSample();accumMs-=interval;}
  draw();
}

function reset(){sampleIdx=0;samples=[];['si','av','qv','ev'].forEach(id=>document.getElementById(id).textContent='—');document.getElementById('log').textContent='reset';draw();}

document.getElementById('freq').oninput=e=>{freq=+e.target.value;document.getElementById('freq-v').textContent=freq+' Hz';reset();};
document.getElementById('sr').oninput=e=>{sr=+e.target.value;document.getElementById('sr-v').textContent=sr+' Hz';reset();};
document.getElementById('bits').oninput=e=>{bits=+e.target.value;document.getElementById('bits-v').textContent=bits+' bits = '+Math.pow(2,bits)+' levels';reset();};
document.getElementById('spd').oninput=e=>{speed=+e.target.value;const n=['','very slow','slow','med-slow','medium','med-fast','fast','faster','very fast','ultra','max'];document.getElementById('spd-v').textContent=n[speed]||speed;};

document.getElementById('btnPlay').onclick=function(){playing=!playing;this.textContent=playing?'❚❚ pause':'▶ play';this.classList.toggle('active',playing);if(playing){lastTime=performance.now();accumMs=0;}};
document.getElementById('btnStep').onclick=()=>{playing=false;document.getElementById('btnPlay').textContent='▶ play';document.getElementById('btnPlay').classList.remove('active');addSample();draw();};
document.getElementById('btnReset').onclick=reset;
document.getElementById('btnNyq').onclick=()=>{freq=15;sr=20;document.getElementById('freq').value=15;document.getElementById('sr').value=20;document.getElementById('freq-v').textContent='15 Hz';document.getElementById('sr-v').textContent='20 Hz';reset();playing=true;document.getElementById('btnPlay').textContent='❚❚ pause';document.getElementById('btnPlay').classList.add('active');};
document.getElementById('btnLow').onclick=()=>{bits=2;freq=3;sr=30;document.getElementById('bits').value=2;document.getElementById('freq').value=3;document.getElementById('sr').value=30;document.getElementById('bits-v').textContent='2 bits = 4 levels';document.getElementById('freq-v').textContent='3 Hz';document.getElementById('sr-v').textContent='30 Hz';reset();playing=true;document.getElementById('btnPlay').textContent='❚❚ pause';document.getElementById('btnPlay').classList.add('active');};

lastTime=performance.now();
rafId=requestAnimationFrame(loop);
</script>
</body>
</html>
"""


def show_animation_ui() -> None:
    st.header("Sampling Animation")
    st.markdown(
        "Watch the ADC sampling process happen in real time — "
        "each sample is taken from the analog signal, then snapped to the nearest "
        "quantization level. The **green dot** is the sample, the **orange dot** is "
        "after quantization, the connecting line is the error."
    )

    col1, col2, col3 = st.columns(3)
    col1.info("Green dot = analog sample point")
    col2.warning("Orange dot = quantized level")
    col3.error("Red cursor = aliasing detected")

    components.html(ANIMATION_HTML, height=620, scrolling=False)

    with st.expander("What you are seeing"):
        st.markdown("""
**Analog signal (blue)** — the continuous sine wave the ADC is measuring.

**Quantization levels (dashed lines)** — the allowed output values. More bits = more lines = finer resolution.

**Green stem + dot** — the moment a sample is taken. The dot is the exact analog value at that time.

**Orange dot** — the quantized value. The ADC rounds the green dot to the nearest dashed line.

**Orange line between dots** — quantization error. The shorter this line, the better the ADC.

**Orange staircase** — the reconstructed digital signal. More bits = smoother staircase.

**Test aliasing button** — sets frequency > Nyquist limit. The cursor turns red and the sine wave the ADC captures is completely wrong.

**Step once** — advances exactly one sample at a time. Use this to see each quantization decision individually.
        """)
