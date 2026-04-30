// ============================================================
//  FastRoute map.js  v2.0  — Multi-algorithm Route Optimiser
// ============================================================
const API = "http://127.0.0.1:8000";

const VEHICLE_PALETTE = [
  "#58a6ff","#3fb950","#f0883e","#bc8cff","#ff5555","#ffd700",
  "#00d4aa","#ff6eb4","#8be9fd","#50fa7b","#ffb86c","#bd93f9",
  "#6cb4ff","#e66767","#a8d8a8","#c9a0dc"
];
const ALGO_COLORS = {
  "Nearest Neighbour": "#ff5555",
  "2-Opt Local Search": "#f0883e",
  "Greedy Edge Insertion": "#ffd700",
  "OR-Tools (GLS)": "#3fb950",
};

// ── State ────────────────────────────────────────────────────────────────────
let map, mode = "path", useRoads = false;
let pathStart = null, pathEnd = null;
let tspStart = null, tspMarkers = [];
let depotMarker = null, cvrpMarkers = [], cvrpDemands = [];
let compareMarkers = [], comparePoints = [];
let vehicles = [];
let routeLayers = [];
let lastExportData = null;
let activeBenchmark = null;

// ── Init Map ─────────────────────────────────────────────────────────────────
function initMap() {
  map = L.map("map", { center: [20.5937, 78.9629], zoom: 5, zoomControl: true });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors", maxZoom: 19
  }).addTo(map);
  map.on("dblclick", onMapDblClick);
  for (let i = 0; i < 4; i++) addVehicle();
  renderVehicles();
}

// ── Helpers ──────────────────────────────────────────────────────────────────
const fmt = (lat, lng) => `${lat.toFixed(4)}, ${lng.toFixed(4)}`;

function makeIcon(cls, label) {
  return L.divIcon({ className: `custom-marker ${cls}`, html: label, iconSize: [28,28], iconAnchor:[14,14] });
}

function toast(msg, type="info", dur=3000) {
  const c = document.getElementById("toastContainer");
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${{info:"ℹ",success:"✓",error:"✗"}[type]}</span> ${msg}`;
  c.appendChild(t);
  setTimeout(() => t.remove(), dur);
}

function setStatus(msg, busy=false) {
  document.getElementById("statusText").textContent = msg;
  document.getElementById("statusDot").style.background = busy ? "#f0883e" : "#3fb950";
}

function setCoordBox(valId, boxId, lat, lng) {
  const el = document.getElementById(valId);
  el.textContent = fmt(lat, lng);
  el.classList.add("has-val");
  document.getElementById(boxId)?.classList.add("set");
}

function resetCoordBox(valId, boxId) {
  const el = document.getElementById(valId);
  el.textContent = "—"; el.classList.remove("has-val");
  document.getElementById(boxId)?.classList.remove("set");
}

function btnLoading(id, on) {
  const b = document.getElementById(id);
  b.classList.toggle("loading", on);
  if (!on) b.textContent = b.dataset.label;
  else b.textContent = "Solving…";
}

function showOverlay(rows) {
  const o = document.getElementById("statsOverlay");
  o.innerHTML = rows.map(([k,v]) => `<div class="map-overlay-row"><span class="map-overlay-key">${k}</span><span class="map-overlay-val">${v}</span></div>`).join("");
  o.classList.add("visible");
}

function clearRoutes() {
  routeLayers.forEach(l => map.removeLayer(l));
  routeLayers = [];
  document.getElementById("statsOverlay").classList.remove("visible");
}

function haversineKm(a, b) {
  const R=6371, dLat=(b[0]-a[0])*Math.PI/180, dLng=(b[1]-a[1])*Math.PI/180;
  const x = Math.sin(dLat/2)**2 + Math.cos(a[0]*Math.PI/180)*Math.cos(b[0]*Math.PI/180)*Math.sin(dLng/2)**2;
  return R*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));
}

function routeDistKm(coords) {
  let d=0; for(let i=1;i<coords.length;i++) d+=haversineKm(coords[i-1],coords[i]);
  return d.toFixed(2);
}

// ── Mode Switch ───────────────────────────────────────────────────────────────
const HINTS = {
  path:    "Double-click map to set Start, then End point.",
  tsp:     "Double-click to set Start, then add stops. Need ≥3 total.",
  cvrp:    "Double-click for Depot, then add customers with demands.",
  compare: "Load a benchmark OR double-click to place custom points (≥4).",
};

document.querySelectorAll(".mode-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active","path","tsp","cvrp","compare"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active", btn.dataset.mode);
    document.getElementById(`panel-${btn.dataset.mode}`).classList.add("active");
    mode = btn.dataset.mode;
    document.getElementById("instrText").textContent = HINTS[mode];
  });
});

// ── Theme ─────────────────────────────────────────────────────────────────────
document.getElementById("themeToggle").addEventListener("click", () => {
  document.body.classList.toggle("light");
  document.getElementById("themeToggle").textContent = document.body.classList.contains("light") ? "🌞" : "🌙";
});

// ── Roads Toggle ─────────────────────────────────────────────────────────────
document.getElementById("roadsToggle").addEventListener("click", () => {
  useRoads = !useRoads;
  document.getElementById("roadsToggle").classList.toggle("active", useRoads);
  document.getElementById("roadsBadge").textContent = useRoads ? "🛣 Road Distances" : "📐 Haversine";
  document.getElementById("roadsBadge").classList.toggle("roads-on", useRoads);
  toast(useRoads ? "Road distances ON (OSRM)" : "Switched to Haversine", "info");
});

// ── Export ────────────────────────────────────────────────────────────────────
document.getElementById("exportBtn").addEventListener("click", () => {
  if (!lastExportData) { toast("No results to export yet", "error"); return; }
  const blob = new Blob([JSON.stringify(lastExportData, null, 2)], { type:"application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = `fastroute_${mode}_${Date.now()}.json`; a.click();
  toast("Results exported", "success");
});

// ── Reset ────────────────────────────────────────────────────────────────────
document.getElementById("resetBtn").addEventListener("click", resetAll);

function resetAll() {
  [pathStart, pathEnd, tspStart, depotMarker].forEach(m => { if(m) map.removeLayer(m); });
  [...tspMarkers, ...cvrpMarkers, ...compareMarkers].forEach(m => map.removeLayer(m));
  clearRoutes();
  pathStart=pathEnd=null; tspStart=null;
  tspMarkers=[]; cvrpMarkers=[]; cvrpDemands=[];
  compareMarkers=[]; comparePoints=[]; activeBenchmark=null;
  depotMarker=null;
  ["startCoord","endCoord","tspStartCoord","depotCoord"].forEach(id => {
    const box = {startCoord:"box-start",endCoord:"box-end",tspStartCoord:"box-tsp-start",depotCoord:"box-depot"}[id];
    resetCoordBox(id, box);
  });
  ["tspList","cvrpList","compareList"].forEach(id => {
    const empties = {tspList:"No stops added yet",cvrpList:"No customers yet",compareList:"Double-click map to add points"};
    document.getElementById(id).innerHTML = `<div class="loc-empty">${empties[id]}</div>`;
  });
  ["tspBadge","cvrpBadge","compareBadge"].forEach(id => {
    document.getElementById(id).textContent="0"; document.getElementById(id).classList.remove("has-items");
  });
  document.querySelectorAll(".result-card").forEach(c=>c.classList.add("hidden"));
  document.getElementById("compareResults").classList.add("hidden");
  document.querySelectorAll(".bench-btn").forEach(b=>b.classList.remove("active"));
  lastExportData=null;
  setStatus("Ready");
  toast("Map reset","info",1500);
}

// ── dblclick dispatcher ───────────────────────────────────────────────────────
function onMapDblClick(e) {
  if (mode==="path")    handlePathClick(e);
  else if (mode==="tsp")  handleTspClick(e);
  else if (mode==="cvrp") handleCvrpClick(e);
  else if (mode==="compare") handleCompareClick(e);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  PATH MODE
// ═══════════════════════════════════════════════════════════════════════════════
function handlePathClick(e) {
  const {lat,lng} = e.latlng;
  if (!pathStart) {
    if (pathEnd) { map.removeLayer(pathEnd); pathEnd=null; resetCoordBox("endCoord","box-end"); }
    pathStart = L.marker([lat,lng],{icon:makeIcon("start-marker","S")}).addTo(map).bindPopup("Start");
    setCoordBox("startCoord","box-start",lat,lng); clearRoutes();
    toast("Start set — place End","info");
  } else if (!pathEnd) {
    pathEnd = L.marker([lat,lng],{icon:makeIcon("end-marker","E")}).addTo(map).bindPopup("End");
    setCoordBox("endCoord","box-end",lat,lng);
    toast("End set — click Solve!","success");
  } else {
    map.removeLayer(pathStart); map.removeLayer(pathEnd); pathEnd=null;
    resetCoordBox("endCoord","box-end"); clearRoutes();
    pathStart = L.marker([lat,lng],{icon:makeIcon("start-marker","S")}).addTo(map).bindPopup("Start");
    setCoordBox("startCoord","box-start",lat,lng);
    toast("Start moved — place End","info");
  }
}

document.getElementById("solvePathBtn").addEventListener("click", async () => {
  if (!pathStart||!pathEnd) { toast("Place Start and End first","error"); return; }
  btnLoading("solvePathBtn",true); clearRoutes(); setStatus("Fetching road route…",true);
  try {
    const s=pathStart.getLatLng(), e=pathEnd.getLatLng();
    const res = await fetch(`${API}/path`,{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({points:[[s.lat,s.lng],[e.lat,e.lng]]})});
    const data = await res.json();
    if (!data.route?.length) { toast("No path found","error"); return; }
    const d = data.distance > 0 ? data.distance.toFixed(2) : routeDistKm(data.route);
    const roadType = data.used_roads ? "Road (OSRM)" : "Straight line (OSRM offline)";
    const waypoints = data.route.length;
    const line = L.polyline(data.route,{
      color: data.used_roads ? "#3fb950" : "#58a6ff",
      weight:5, opacity:.9,
    }).addTo(map);
    routeLayers.push(line);
    map.fitBounds(line.getBounds(),{padding:[50,50]});
    showOverlay([["Mode","Shortest Path"],["Route type",roadType],["Distance",`${d} km`],["Road points",waypoints]]);
    showResultCard("pathResult",[["Distance",`${d} km`,"good"],["Route type",roadType],["Waypoints",waypoints]]);
    lastExportData = {mode:"path",route:data.route,distance_km:d,used_roads:data.used_roads};
    setStatus(`Path found — ${d} km`);
    toast(`Road route: ${d} km (${waypoints} pts)`,"success");
  } catch(err) { toast("Server error — is backend running?","error"); setStatus("Error"); }
  finally { btnLoading("solvePathBtn",false); }
});

// ═══════════════════════════════════════════════════════════════════════════════
//  TSP MODE
// ═══════════════════════════════════════════════════════════════════════════════
function handleTspClick(e) {
  const {lat,lng}=e.latlng;
  if (!tspStart) {
    tspStart=L.marker([lat,lng],{icon:makeIcon("start-marker","S")}).addTo(map).bindPopup("TSP Start");
    setCoordBox("tspStartCoord","box-tsp-start",lat,lng);
    toast("Start set — add stops","info");
  } else {
    const n=tspMarkers.length+1;
    const m=L.marker([lat,lng],{icon:makeIcon("customer-marker",n)}).addTo(map).bindPopup(`Stop ${n}`);
    tspMarkers.push(m); updateTspList();
    toast(`Stop ${n} added`,"info",1500);
  }
}

function updateTspList() {
  const list=document.getElementById("tspList"), badge=document.getElementById("tspBadge");
  badge.textContent=tspMarkers.length; badge.classList.toggle("has-items",tspMarkers.length>0);
  list.innerHTML=tspMarkers.length===0
    ? `<div class="loc-empty">No stops added yet</div>`
    : tspMarkers.map((m,i)=>{const ll=m.getLatLng();return`<div class="loc-item"><span class="loc-num">${i+1}</span>${fmt(ll.lat,ll.lng)}</div>`;}).join("");
}

document.getElementById("solveTspBtn").addEventListener("click", async () => {
  if (!tspStart||tspMarkers.length<2) { toast("Need Start + ≥2 stops","error"); return; }
  btnLoading("solveTspBtn",true); clearRoutes(); setStatus("Solving TSP…",true);
  try {
    const s=tspStart.getLatLng();
    const pts=[[s.lat,s.lng],...tspMarkers.map(m=>{const ll=m.getLatLng();return[ll.lat,ll.lng];})];
    const res=await fetch(`${API}/tsp`,{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({points:pts,use_roads:useRoads})});
    const data=await res.json();
    if (!data.route?.length) { toast("No TSP solution","error"); return; }
    const line=L.polyline(data.route,{color:"#3fb950",weight:4,opacity:.9,dashArray:"10 4"}).addTo(map);
    routeLayers.push(line);
    map.fitBounds(line.getBounds(),{padding:[40,40]});
    const d=data.distance||routeDistKm(data.route);
    showOverlay([["Mode","TSP (OR-Tools)"],["Stops",tspMarkers.length],["Total",`${d} km`]]);
    showResultCard("tspResult",[["Algorithm","OR-Tools GLS"],["Stops",tspMarkers.length],["Distance",`${d} km`,"good"],["Distance type",useRoads?"Road":"Haversine"]]);
    lastExportData={mode:"tsp",algorithm:"OR-Tools GLS",route:data.route,distance_km:d,stops:tspMarkers.length};
    setStatus(`TSP solved — ${d} km`);
    toast(`TSP: ${d} km`,"success");
  } catch { toast("Server error","error"); setStatus("Error"); }
  finally { btnLoading("solveTspBtn",false); }
});

// ═══════════════════════════════════════════════════════════════════════════════
//  CVRP MODE
// ═══════════════════════════════════════════════════════════════════════════════
function handleCvrpClick(e) {
  const {lat,lng}=e.latlng;
  if (!depotMarker) {
    depotMarker=L.marker([lat,lng],{icon:makeIcon("depot-marker","D")}).addTo(map).bindPopup("Depot");
    setCoordBox("depotCoord","box-depot",lat,lng);
    toast("Depot set — add customers","info");
  } else {
    const demand=parseInt(prompt(`Demand for Customer ${cvrpMarkers.length+1}:`,"10"));
    if (isNaN(demand)||demand<=0) { toast("Invalid demand","error"); return; }
    const n=cvrpMarkers.length+1;
    const m=L.marker([lat,lng],{icon:makeIcon("customer-marker",n)}).addTo(map).bindPopup(`C${n} (demand:${demand})`);
    cvrpMarkers.push(m); cvrpDemands.push(demand); updateCvrpList();
    toast(`Customer ${n} added (×${demand})`,"info",1500);
  }
}

function updateCvrpList() {
  const list=document.getElementById("cvrpList"), badge=document.getElementById("cvrpBadge");
  badge.textContent=cvrpMarkers.length; badge.classList.toggle("has-items",cvrpMarkers.length>0);
  list.innerHTML=cvrpMarkers.length===0
    ? `<div class="loc-empty">No customers yet</div>`
    : cvrpMarkers.map((m,i)=>{const ll=m.getLatLng();return`<div class="loc-item"><span class="loc-num">${i+1}</span>${fmt(ll.lat,ll.lng)}<span class="loc-demand">×${cvrpDemands[i]}</span></div>`;}).join("");
}

function addVehicle() { vehicles.push({id:vehicles.length,capacity:100}); }

function renderVehicles() {
  const list=document.getElementById("vehiclesList");
  list.innerHTML=vehicles.length===0
    ? `<div class="loc-empty">No vehicles</div>`
    : vehicles.map((v,i)=>`
      <div class="vehicle-item">
        <div class="vehicle-swatch" style="background:${VEHICLE_PALETTE[i%VEHICLE_PALETTE.length]}"></div>
        <span class="vehicle-name">Vehicle ${i+1}</span>
        <span class="vehicle-cap-label">Cap</span>
        <input class="cap-input" type="number" min="1" value="${v.capacity}" onchange="vehicles[${i}].capacity=parseInt(this.value)||100"/>
        <button class="remove-vehicle-btn" onclick="removeVehicle(${i})">✕</button>
      </div>`).join("");
}

function removeVehicle(idx) {
  if(vehicles.length<=1){toast("Need at least 1 vehicle","error");return;}
  vehicles.splice(idx,1); renderVehicles();
}

document.getElementById("addVehicleBtn").addEventListener("click",()=>{ addVehicle(); renderVehicles(); toast(`Vehicle ${vehicles.length} added`,"info",1500); });

document.getElementById("solveCvrpBtn").addEventListener("click", async () => {
  if (!depotMarker){toast("Place Depot first","error");return;}
  if (!cvrpMarkers.length){toast("Add at least 1 customer","error");return;}
  if (!vehicles.length){toast("Add at least 1 vehicle","error");return;}
  const totalDemand=cvrpDemands.reduce((a,b)=>a+b,0);
  const totalCap=vehicles.reduce((a,v)=>a+v.capacity,0);
  if(totalDemand>totalCap){toast(`Total demand ${totalDemand} > fleet capacity ${totalCap}. Add vehicles or increase capacity.`,"error",5000);return;}
  btnLoading("solveCvrpBtn",true); clearRoutes(); setStatus("Solving CVRP…",true);
  try {
    const dl=depotMarker.getLatLng();
    const res=await fetch(`${API}/cvrp`,{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        depot:[dl.lat,dl.lng],
        customers:cvrpMarkers.map(m=>{const ll=m.getLatLng();return[ll.lat,ll.lng];}),
        demands:cvrpDemands,
        capacities:vehicles.map(v=>v.capacity),
        use_roads:useRoads
      })});
    const data=await res.json();
    if(!data.routes?.length){toast("No CVRP solution — adjust capacities","error");return;}
    data.routes.forEach((route,i)=>{
      const color=VEHICLE_PALETTE[i%VEHICLE_PALETTE.length];
      routeLayers.push(L.polyline(route,{color,weight:4,opacity:.9}).addTo(map));
    });
    const allCoords=data.routes.flat();
    if(allCoords.length) map.fitBounds(L.latLngBounds(allCoords),{padding:[40,40]});
    const d=data.total_distance||"—";
    showOverlay([["Mode","CVRP"],["Vehicles used",data.vehicles_used],["Customers",cvrpMarkers.length],["Total dist",`${d} km`]]);
    showResultCard("cvrpResult",[["Vehicles used",data.vehicles_used,"good"],["Customers",cvrpMarkers.length],["Total demand",totalDemand],["Total distance",`${d} km`,"good"]]);
    lastExportData={mode:"cvrp",routes:data.routes,vehicles_used:data.vehicles_used,total_distance_km:d};
    setStatus(`CVRP solved — ${data.vehicles_used} routes`);
    toast(`CVRP: ${data.vehicles_used} routes, ${d} km`,"success");
  } catch { toast("Server error","error"); setStatus("Error"); }
  finally { btnLoading("solveCvrpBtn",false); }
});

// ═══════════════════════════════════════════════════════════════════════════════
//  COMPARE MODE
// ═══════════════════════════════════════════════════════════════════════════════
document.querySelectorAll(".bench-btn").forEach(btn=>{
  btn.addEventListener("click", async ()=>{
    document.querySelectorAll(".bench-btn").forEach(b=>b.classList.remove("active"));
    btn.classList.add("active");
    const name=btn.dataset.bench;
    if(name==="custom"){ activeBenchmark=null; toast("Place points on map","info"); return; }
    try {
      const res=await fetch(`${API}/benchmarks/${name}`);
      const data=await res.json();
      // clear existing compare markers
      compareMarkers.forEach(m=>map.removeLayer(m)); compareMarkers=[]; comparePoints=[];
      data.points.forEach((p,i)=>{
        const m=L.marker(p,{icon:makeIcon("compare-marker",i+1)}).addTo(map).bindPopup(`Point ${i+1}`);
        compareMarkers.push(m); comparePoints.push(p);
      });
      if(comparePoints.length) map.fitBounds(L.latLngBounds(comparePoints),{padding:[40,40]});
      updateCompareList();
      activeBenchmark=data;
      toast(`Loaded: ${data.name} (${data.points.length} pts)`,"success");
    } catch { toast("Could not load benchmark","error"); }
  });
});

function handleCompareClick(e) {
  const {lat,lng}=e.latlng;
  const n=comparePoints.length+1;
  const m=L.marker([lat,lng],{icon:makeIcon("compare-marker",n)}).addTo(map).bindPopup(`Point ${n}`);
  compareMarkers.push(m); comparePoints.push([lat,lng]);
  updateCompareList();
}

function updateCompareList() {
  const list=document.getElementById("compareList"), badge=document.getElementById("compareBadge");
  badge.textContent=comparePoints.length; badge.classList.toggle("has-items",comparePoints.length>0);
  list.innerHTML=comparePoints.length===0
    ? `<div class="loc-empty">Double-click map to add points</div>`
    : comparePoints.map((p,i)=>`<div class="loc-item"><span class="loc-num">${i+1}</span>${fmt(p[0],p[1])}</div>`).join("");
}

// Track per-algorithm polylines for toggling
let compareRouteLayers = {};
let activeCompareRoute = null;

document.getElementById("solveCompareBtn").addEventListener("click", async ()=>{
  if(comparePoints.length<4){toast("Need at least 4 points","error");return;}
  btnLoading("solveCompareBtn",true); clearRoutes();
  // clear old compare route layers
  Object.values(compareRouteLayers).forEach(l=>{ if(l) map.removeLayer(l); });
  compareRouteLayers={};
  setStatus("Running all algorithms…",true);
  document.getElementById("compareResults").classList.add("hidden");
  try {
    const res=await fetch(`${API}/compare`,{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({points:comparePoints})});
    const data=await res.json();
    if(!data.results?.length){toast("No results returned","error");return;}

    // Draw ALL 4 routes on the map using real road geometry
    data.results.forEach((r, i) => {
      const color = ALGO_COLORS[r.algorithm] || "#58a6ff";
      // Use road_route (actual roads) if available, else fallback to straight waypoints
      const coords = (r.road_route && r.road_route.length > 2) ? r.road_route : r.route;
      const isBest = i === 0;
      const line = L.polyline(coords, {
        color,
        weight: isBest ? 5 : 3,
        opacity: isBest ? 0.95 : 0.45,
        dashArray: isBest ? null : "8 5",
      }).addTo(map);
      line.bindTooltip(`${r.rank === 1 ? "🥇 " : ""}${r.algorithm}<br>${r.distance} km`, {sticky:true});
      compareRouteLayers[r.algorithm] = line;
      routeLayers.push(line);
    });

    // Fit map to best route
    const best = data.results[0];
    const bestCoords = (best.road_route?.length > 2) ? best.road_route : best.route;
    if(bestCoords.length) map.fitBounds(L.latLngBounds(bestCoords),{padding:[50,50]});

    renderCompareResults(data.results);
    lastExportData={mode:"compare",point_count:comparePoints.length,results:data.results};
    setStatus(`Compare done — best: ${best.algorithm}`);
    toast(`All 4 routes drawn — best: ${best.algorithm} @ ${best.distance} km`,"success");
  } catch(e) { toast("Server error","error"); setStatus("Error"); console.error(e); }
  finally { btnLoading("solveCompareBtn",false); }
});

// Toggle individual algorithm routes on/off
function toggleCompareRoute(algo) {
  const layer = compareRouteLayers[algo];
  if (!layer) return;
  if (map.hasLayer(layer)) {
    map.removeLayer(layer);
  } else {
    layer.addTo(map);
  }
}

function renderCompareResults(results) {
  const el=document.getElementById("compareResults");
  el.classList.remove("hidden");

  // table with route toggle buttons
  const table=document.getElementById("compareTable");
  table.innerHTML=`
    <tr><th>#</th><th>Algorithm</th><th>Distance</th><th>Time</th><th>Gap</th><th>Map</th></tr>
    ${results.map((r,i)=>{
      const gapClass=r.gap_pct===0?"gap-0":r.gap_pct<10?"gap-mid":"gap-hi";
      const medal=i===0?"🥇":i===1?"🥈":i===2?"🥉":"#"+r.rank;
      const color=ALGO_COLORS[r.algorithm]||"#58a6ff";
      const routeType=(r.road_route&&r.road_route.length>2)?"🛣":"📐";
      return`<tr class="rank-${r.rank}">
        <td>${medal}</td>
        <td style="color:${color};font-weight:600">${r.algorithm}</td>
        <td>${r.distance} km ${routeType}</td>
        <td>${r.time_ms} ms</td>
        <td><span class="gap-badge ${gapClass}">+${r.gap_pct}%</span></td>
        <td><button class="toggle-route-btn" onclick="toggleCompareRoute('${r.algorithm}')" style="border-color:${color};color:${color}">👁</button></td>
      </tr>`;
    }).join("")}`;

  // Legend
  const legendHtml = results.map(r=>{
    const color=ALGO_COLORS[r.algorithm]||"#58a6ff";
    const isBest=r.rank===1;
    return `<span class="legend-item"><span class="legend-dot" style="background:${color};${isBest?"box-shadow:0 0 6px "+color:"opacity:.5"}"></span>${r.algorithm}${isBest?" ✓":""}</span>`;
  }).join("");
  let legend = document.getElementById("compareLegend");
  if(!legend){
    legend=document.createElement("div");
    legend.id="compareLegend";
    legend.className="compare-legend";
    table.parentNode.insertBefore(legend, table.nextSibling);
  }
  legend.innerHTML = `<div class="section-label" style="margin-bottom:5px">Map Legend <span style="font-size:.65rem;color:var(--text3)">(click 👁 to toggle)</span></div>${legendHtml}`;

  // bar chart (distance)
  drawBarChart("barChart", results, r=>r.distance, "km", r=>ALGO_COLORS[r.algorithm]||"#58a6ff");
  // bar chart (time)
  drawBarChart("timeChart", results, r=>r.time_ms, "ms", ()=>"#bc8cff");
}

function drawBarChart(svgId, results, valFn, unit, colorFn) {
  const svg=document.getElementById(svgId);
  const W=280,H=160,padL=6,padR=6,padT=20,padB=30;
  const chartW=W-padL-padR, chartH=H-padT-padB;
  const vals=results.map(valFn);
  const maxVal=Math.max(...vals)||1;
  const barW=chartW/vals.length-6;
  let html="";
  vals.forEach((v,i)=>{
    const bh=Math.max(3,(v/maxVal)*chartH);
    const x=padL+i*(barW+6);
    const y=padT+chartH-bh;
    const color=colorFn(results[i]);
    const label=results[i].algorithm.split(" ")[0];
    html+=`<rect x="${x}" y="${y}" width="${barW}" height="${bh}" fill="${color}" opacity=".85" rx="2"/>`;
    html+=`<text x="${x+barW/2}" y="${y-4}" fill="${color}" font-size="9" text-anchor="middle" font-family="JetBrains Mono">${v}</text>`;
    html+=`<text x="${x+barW/2}" y="${H-8}" fill="#8b9ab0" font-size="8" text-anchor="middle">${label}</text>`;
  });
  // y axis
  html+=`<text x="2" y="${padT}" fill="#4d5f7a" font-size="8">${unit}</text>`;
  svg.innerHTML=html;
}

// ── Result card helper ────────────────────────────────────────────────────────
function showResultCard(id, rows) {
  const card=document.getElementById(id);
  card.classList.remove("hidden");
  card.innerHTML=rows.map(([k,v,cls])=>`
    <div class="result-row">
      <span class="result-key">${k}</span>
      <span class="result-val${cls?" "+cls:""}">${v}</span>
    </div>`).join("");
}

// ── Boot ──────────────────────────────────────────────────────────────────────
initMap();
setStatus("Ready");
