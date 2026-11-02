import { leafletCSS, leafletJS } from './leafletAssets';
const escapeScript = (value: string) => value.replace(/<\/script/gi, '<\\/script');
export function mapHTML(offline: boolean, dark: boolean) {
  const base = `<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1"><style>html,body,#map{margin:0;width:100%;height:100%;background:${dark ? '#091624' : '#f8f5ed'};-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}.label{color:${dark ? '#c1d5eb' : '#60788d'};font:10px sans-serif;white-space:nowrap} .leaflet-tooltip{border:0;background:transparent;box-shadow:none}.leaflet-control-attribution{font-size:9px}</style>`;
  if (offline) return `<!doctype html><html><head>${base}<style>${leafletCSS}</style></head><body><div id="map"></div><script>${escapeScript(leafletJS)}</script><script>
  let lastTap=0,lastSent=0;function send(lng,lat){const t=Date.now();if(t-lastSent<800)return;lastSent=t;window.ReactNativeWebView.postMessage(JSON.stringify({type:'destination',longitude:lng,latitude:lat}));}function tap(lng,lat){const t=Date.now();if(t-lastTap<600){lastTap=0;send(lng,lat);}else lastTap=t;}
  function toLngLat(x,y){const l=map.containerPointToLatLng([x,y]);return [l.lng,l.lat];}let ts=null,tp=null;document.addEventListener('touchstart',e=>{const t=e.touches[0];ts={x:t.clientX,y:t.clientY,t:Date.now()};},{capture:true,passive:true});document.addEventListener('touchend',e=>{const t=e.changedTouches[0],n=Date.now(),s=ts;ts=null;if(!s||Math.hypot(t.clientX-s.x,t.clientY-s.y)>12||n-s.t>350)return;if(tp&&n-tp.t<600&&Math.hypot(t.clientX-tp.x,t.clientY-tp.y)<40){tp=null;const c=toLngLat(t.clientX,t.clientY);if(c)send(c[0],c[1]);}else tp={x:t.clientX,y:t.clientY,t:n};},{capture:true,passive:true});
  const map=L.map('map',{zoomControl:false,doubleClickZoom:false,attributionControl:true}).setView([20.57,-101.195],15);
  map.attributionControl.addAttribution('© OpenStreetMap contributors');
  let roads=L.layerGroup().addTo(map),routes=L.layerGroup().addTo(map),incidents=L.layerGroup().addTo(map),heat=L.layerGroup().addTo(map),gps=L.layerGroup().addTo(map);
  let loaded='';
  function update(data){
    if(!data.hasPackage && loaded){roads.clearLayers();loaded='';}
    if(data.package && loaded!==data.package.metadata.created_at){roads.clearLayers();L.geoJSON(data.package,{style:{color:'${dark ? '#3c5974' : '#bccad8'}',weight:3},onEachFeature:(f,l)=>{if(f.properties.name){const label=document.createElement('span');label.textContent=f.properties.name;l.bindTooltip(label,{sticky:true});}}}).addTo(roads); loaded=data.package.metadata.created_at;}
    routes.clearLayers();incidents.clearLayers();heat.clearLayers();gps.clearLayers();
    (data.routes||[]).forEach(r=>L.geoJSON(r.geometry,{style:{color:r.id===data.selected?'#176fe8':'#8aabc8',weight:r.id===data.selected?7:4}}).addTo(routes));
    (data.incidents||[]).forEach(i=>L.marker([i.latitude,i.longitude],{icon:L.divIcon({className:'',iconSize:[30,30],html:'<div style="width:30px;height:30px;border-radius:50%;border:3px solid #fff;box-sizing:border-box;box-shadow:0 2px 6px rgba(0,0,0,.35);background:radial-gradient(circle at 35% 30%,'+(i.critical?'#ff8a98,#b83f50':'#ffd36b,#d98a00')+')"></div>'})}).on('click',()=>window.ReactNativeWebView.postMessage(JSON.stringify({type:'incident',id:i.id}))).addTo(incidents));
    if(data.heat)(data.heat.features||[]).forEach(f=>L.circle([f.geometry.coordinates[1],f.geometry.coordinates[0]],{radius:Math.min(300,60+f.properties.weight*25),color:'#b83f50',fillOpacity:.15,weight:0}).addTo(heat));
    if(data.location){L.circleMarker([data.location.latitude,data.location.longitude],{radius:7,color:'#fff',weight:3,fillColor:'#176fe8',fillOpacity:1}).addTo(gps);if(data.recenter)map.setView([data.location.latitude,data.location.longitude],16);}
  }
  window.receive=update;
  map.on('click',e=>tap(e.latlng.lng,e.latlng.lat));map.on('dblclick',e=>send(e.latlng.lng,e.latlng.lat));
  window.ReactNativeWebView.postMessage(JSON.stringify({type:'ready'}));
  </script></body></html>`;
  return `<!doctype html><html><head>${base}<link rel="stylesheet" href="https://atlas.microsoft.com/sdk/javascript/mapcontrol/3/atlas.min.css"><script src="https://atlas.microsoft.com/sdk/javascript/mapcontrol/3/atlas.min.js"></script></head><body><div id="map"></div><script>
  let lastTap=0,lastSent=0;function send(lng,lat){const t=Date.now();if(t-lastSent<800)return;lastSent=t;window.ReactNativeWebView.postMessage(JSON.stringify({type:'destination',longitude:lng,latitude:lat}));}function tap(lng,lat){const t=Date.now();if(t-lastTap<600){lastTap=0;send(lng,lat);}else lastTap=t;}
  function toLngLat(x,y){try{return map&&map.pixelsToPositions([[x,y]])[0];}catch{return null;}}let ts=null,tp=null;document.addEventListener('touchstart',e=>{const t=e.touches[0];ts={x:t.clientX,y:t.clientY,t:Date.now()};},{capture:true,passive:true});document.addEventListener('touchend',e=>{const t=e.changedTouches[0],n=Date.now(),s=ts;ts=null;if(!s||Math.hypot(t.clientX-s.x,t.clientY-s.y)>12||n-s.t>350)return;if(tp&&n-tp.t<600&&Math.hypot(t.clientX-tp.x,t.clientY-tp.y)<40){tp=null;const c=toLngLat(t.clientX,t.clientY);if(c)send(c[0],c[1]);}else tp={x:t.clientX,y:t.clientY,t:n};},{capture:true,passive:true});
  let map,source,locationSource,heatSource,token='',api='',ready=false,latest;
  function update(data){
    latest=data;
    token=data.token;api=data.api;
    if(!map){
      if(typeof atlas==='undefined'){window.ReactNativeWebView.postMessage(JSON.stringify({type:'error',message:'No se pudo descargar el visor de Azure Maps. Comprueba tu conexión a internet y reintenta el mapa.'}));return;}
      map=new atlas.Map('map',{dblClickZoomInteraction:false,center:[-101.195,20.57],zoom:14,style:'${dark ? 'night' : 'road'}',language:'es-MX',authOptions:{authType:'anonymous',clientId:'00000000-0000-0000-0000-000000000000',getToken:(resolve)=>resolve(token)},transformRequest:(url,type)=>url.startsWith('https://atlas.microsoft.com/map/')?{url:api+'/api/v1/maps/proxy?url='+encodeURIComponent(url),headers:{Authorization:'Bearer '+token}}:{url}});
      map.events.add('error',()=>window.ReactNativeWebView.postMessage(JSON.stringify({type:'error',message:'No se pudo cargar Azure Maps. Comprueba la conexión y la configuración del servidor.'})));
      map.events.add('ready',()=>{
        ready=true;source=new atlas.source.DataSource();locationSource=new atlas.source.DataSource();heatSource=new atlas.source.DataSource();map.sources.add([source,locationSource,heatSource]);
        map.layers.add(new atlas.layer.HeatMapLayer(heatSource,'heat',{radius:35,opacity:.45,weight:['get','weight']}));
        map.layers.add(new atlas.layer.LineLayer(source,'routes',{filter:['==',['geometry-type'],'LineString'],strokeColor:['case',['get','selected'],'#176fe8','#8aabc8'],strokeWidth:['case',['get','selected'],7,4]}));
        map.layers.add(new atlas.layer.BubbleLayer(source,'incident-halo',{filter:['==',['geometry-type'],'Point'],radius:22,blur:.9,opacity:.55,color:['case',['get','critical'],'#ff8a98','#ffc23d'],strokeWidth:0}));const layer=new atlas.layer.BubbleLayer(source,'incidents',{filter:['==',['geometry-type'],'Point'],radius:12,color:['case',['get','critical'],'#b83f50','#d98a00'],strokeColor:'#ffffff',strokeWidth:3});map.layers.add(layer);
        map.layers.add(new atlas.layer.BubbleLayer(locationSource,'gps',{radius:7,color:'#176fe8',strokeColor:'#ffffff',strokeWidth:3}));
        map.events.add('click',layer,e=>{const shape=e.shapes&&e.shapes[0];if(shape)window.ReactNativeWebView.postMessage(JSON.stringify({type:'incident',id:shape.getProperties().id}));});
        map.events.add('click',e=>{if(!e.shapes||!e.shapes.length)tap(e.position[0],e.position[1]);});map.events.add('dblclick',e=>{if(!e.shapes||!e.shapes.length)send(e.position[0],e.position[1]);});
        window.ReactNativeWebView.postMessage(JSON.stringify({type:'loaded'}));
        update(latest);
      });return;
    }
    if(!ready)return;
    source.clear();locationSource.clear();heatSource.clear();
    (data.routes||[]).forEach(r=>source.add({type:'Feature',geometry:r.geometry,properties:{selected:r.id===data.selected}}));
    (data.incidents||[]).forEach(i=>source.add({type:'Feature',geometry:{type:'Point',coordinates:[i.longitude,i.latitude]},properties:{id:i.id,critical:i.critical}}));
    if(data.heat)heatSource.add(data.heat);
    if(data.location){locationSource.add(new atlas.data.Point([data.location.longitude,data.location.latitude]));if(data.recenter)map.setCamera({center:[data.location.longitude,data.location.latitude],zoom:16});}
  }
  window.setSessionToken=value=>{token=value};window.receive=update;window.ReactNativeWebView.postMessage(JSON.stringify({type:'ready'}));
  </script></body></html>`;
}
