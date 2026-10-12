import { leafletCSS, leafletJS } from './leafletAssets';
const escapeScript = (value: string) => value.replace(/<\/script/gi, '<\\/script');
export function mapHTML(offline: boolean, dark: boolean) {
  const base = `<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1"><style>html,body,#map{margin:0;width:100%;height:100%;background:${dark ? '#091624' : '#f8f5ed'}}.label{color:${dark ? '#c1d5eb' : '#60788d'};font:10px sans-serif;white-space:nowrap} .leaflet-tooltip{border:0;background:transparent;box-shadow:none}.leaflet-control-attribution{font-size:9px}</style>`;
  if (offline) return `<!doctype html><html><head>${base}<style>${leafletCSS}</style></head><body><div id="map"></div><script>${escapeScript(leafletJS)}</script><script>
  const map=L.map('map',{zoomControl:false,attributionControl:true}).setView([20.57,-101.195],15);
  map.attributionControl.addAttribution('© OpenStreetMap contributors');
  let roads=L.layerGroup().addTo(map),routes=L.layerGroup().addTo(map),incidents=L.layerGroup().addTo(map),heat=L.layerGroup().addTo(map),gps=L.layerGroup().addTo(map);
  let loaded='';
  function update(data){
    if(!data.package && loaded){roads.clearLayers();loaded='';}
    if(data.package && loaded!==data.package.metadata.created_at){roads.clearLayers();L.geoJSON(data.package,{style:{color:'${dark ? '#3c5974' : '#bccad8'}',weight:3},onEachFeature:(f,l)=>{if(f.properties.name){const label=document.createElement('span');label.textContent=f.properties.name;l.bindTooltip(label,{sticky:true});}}}).addTo(roads); loaded=data.package.metadata.created_at;}
    routes.clearLayers();incidents.clearLayers();heat.clearLayers();gps.clearLayers();
    (data.routes||[]).forEach(r=>L.geoJSON(r.geometry,{style:{color:r.id===data.selected?'#176fe8':'#8aabc8',weight:r.id===data.selected?7:4}}).addTo(routes));
    (data.incidents||[]).forEach(i=>L.circleMarker([i.latitude,i.longitude],{radius:i.critical?10:7,color:i.critical?'#b83f50':'#176fe8',fillOpacity:.8}).on('click',()=>window.ReactNativeWebView.postMessage(JSON.stringify({type:'incident',id:i.id}))).addTo(incidents));
    if(data.heat)(data.heat.features||[]).forEach(f=>L.circle([f.geometry.coordinates[1],f.geometry.coordinates[0]],{radius:Math.min(300,60+f.properties.weight*25),color:'#b83f50',fillOpacity:.15,weight:0}).addTo(heat));
    if(data.location){L.circleMarker([data.location.latitude,data.location.longitude],{radius:7,color:'#fff',weight:3,fillColor:'#176fe8',fillOpacity:1}).addTo(gps);if(data.recenter)map.setView([data.location.latitude,data.location.longitude],16);}
  }
  window.receive=update;
  map.on('click',e=>window.ReactNativeWebView.postMessage(JSON.stringify({type:'destination',longitude:e.latlng.lng,latitude:e.latlng.lat})));
  window.ReactNativeWebView.postMessage(JSON.stringify({type:'ready'}));
  </script></body></html>`;
  return `<!doctype html><html><head>${base}<link rel="stylesheet" href="https://atlas.microsoft.com/sdk/javascript/mapcontrol/3/atlas.min.css"><script src="https://atlas.microsoft.com/sdk/javascript/mapcontrol/3/atlas.min.js"></script></head><body><div id="map"></div><script>
  let map,source,locationSource,heatSource,token='',api='',ready=false;
  function update(data){
    token=data.token;api=data.api;
    if(!map){
      map=new atlas.Map('map',{center:[-101.195,20.57],zoom:14,style:'${dark ? 'night' : 'road'}',language:'es-MX',authOptions:{authType:'anonymous',clientId:'00000000-0000-0000-0000-000000000000',getToken:(resolve)=>resolve(token)},transformRequest:(url,type)=>url.startsWith('https://atlas.microsoft.com/map/')?{url:api+'/api/v1/maps/proxy?url='+encodeURIComponent(url),headers:{Authorization:'Bearer '+token}}:{url}});
      map.events.add('error',()=>window.ReactNativeWebView.postMessage(JSON.stringify({type:'error',message:'No se pudo cargar Azure Maps. Comprueba la conexión y la configuración del servidor.'})));
      map.events.add('ready',()=>{
        ready=true;source=new atlas.source.DataSource();locationSource=new atlas.source.DataSource();heatSource=new atlas.source.DataSource();map.sources.add([source,locationSource,heatSource]);
        map.layers.add(new atlas.layer.HeatMapLayer(heatSource,'heat',{radius:35,opacity:.45,weight:['get','weight']}));
        map.layers.add(new atlas.layer.LineLayer(source,'routes',{filter:['==',['geometry-type'],'LineString'],strokeColor:['case',['get','selected'],'#176fe8','#8aabc8'],strokeWidth:['case',['get','selected'],7,4]}));
        const layer=new atlas.layer.BubbleLayer(source,'incidents',{filter:['==',['geometry-type'],'Point'],radius:8,color:['case',['get','critical'],'#b83f50','#176fe8'],strokeColor:'#ffffff',strokeWidth:2});map.layers.add(layer);
        map.layers.add(new atlas.layer.BubbleLayer(locationSource,'gps',{radius:7,color:'#176fe8',strokeColor:'#ffffff',strokeWidth:3}));
        map.events.add('click',layer,e=>{const shape=e.shapes&&e.shapes[0];if(shape)window.ReactNativeWebView.postMessage(JSON.stringify({type:'incident',id:shape.getProperties().id}));});
        map.events.add('click',e=>{if(!e.shapes||!e.shapes.length)window.ReactNativeWebView.postMessage(JSON.stringify({type:'destination',longitude:e.position[0],latitude:e.position[1]}));});
        update(data);
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
