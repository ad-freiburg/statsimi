var msgEle = document.getElementById("msg");

function classify(labelA, labelB, posA, posB) {
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            var content = JSON.parse(this.responseText);
            if (content.res > 0.5) {
                msgEle.innerHTML = "Similar";
                document.body.className = "simi";
            } else {
                msgEle.innerHTML = "Not similar";                
                document.body.className = "notsimi";
            }
        }
    };

    xmlhttp.open("GET", "/api?name1=" + labelA + "&name2=" + labelB + "&lat1=" + posA.lat + "&lon1=" + posA.lng + "&lat2=" + posB.lat + "&lon2=" + posB.lng, true);
    xmlhttp.send();
}

var map = L.map('map', {
  renderer: L.canvas()
}).setView([48.00210, 7.81997], 18);


L.tileLayer('https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png', {
    maxZoom: 23,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attribution">CARTO</a>',
    id: 'mapbox.streets'
}).addTo(map);

var station1pop, station2pop;

function makeDraggable(popup) {
  var pos = map.latLngToLayerPoint(popup.getLatLng());
  L.DomUtil.setPosition(popup._wrapper.parentNode, pos);
  var draggable = new L.Draggable(popup._container, popup._wrapper);
  draggable.enable();
  
  draggable.on('dragend', function() {
    var pos = map.layerPointToLatLng(this._newPos);
    popup.setLatLng(pos);
    popup.posEl.innerHTML = pos.lat.toFixed(5) + ", " + pos.lng.toFixed(5);
    reclassify();
  });

  popup.draggable = draggable;
}

function reclassify() {
    if (station1pop !== undefined && station2pop !== undefined) {
        var lbl1 = station1pop.getContent().getElementsByTagName("input")[0].value.trim();        
        var lbl2 = station2pop.getContent().getElementsByTagName("input")[0].value.trim();
        var pos1 = station1pop.getLatLng();
        var pos2 = station2pop.getLatLng();
        classify(lbl1, lbl2, pos1, pos2);
    } else {
        document.body.className = "";
    }
}

function openStat(latlng, label) {
    if (station1pop !== undefined && station2pop !== undefined) return;

    var div = document.createElement('div');
    var ico = document.createElement('div');
    var inp = document.createElement('input');
    inp.type = "text";
    inp.oninput = function() {reclassify();}
    var pos = document.createElement('span');
    pos.innerHTML = latlng.lat.toFixed(5) + ", " + latlng.lng.toFixed(5);
    pos.className = "pos";
    ico.className = "ico";

    var close = document.createElement('span');
    close.className = "close";

    div.append(inp);
    div.append(pos);
    div.append(close);
    div.append(ico);

    if (station1pop === undefined) {
        station1pop = L.popup({closeOnClick: false, autoClose: false, closeButton: false, className: 'pop1'})
            .setLatLng(latlng)
            .setContent(div)
            .openOn(map)
            .on("remove", function() {
                if (station1pop == this) station1pop = undefined;
                reclassify();
            });
        station1pop.posEl = pos;
        inp.value = label;
        makeDraggable(station1pop);
        close.onclick = function() {station1pop.remove();}
        inp.onmouseenter = function() { if (!station1pop.draggable._moving) station1pop.draggable.disable(); }
        inp.onmouseleave = function() { station1pop.draggable.enable();  }
    } else if (station2pop === undefined) {
        station2pop = L.popup({closeOnClick: false, autoClose: false, closeButton: false, className: 'pop2'})
            .setLatLng(latlng)
            .setContent(div)
            .openOn(map)
            .on("remove", function() {
                if (station2pop == this) station2pop = undefined;
                reclassify();
            });
        station2pop.posEl = pos;
        inp.value = label;
        makeDraggable(station2pop);
        close.onclick = function() {station2pop.remove();}
        inp.onmouseenter = function() { if (!station2pop.draggable._moving) station2pop.draggable.disable(); }
        inp.onmouseleave = function() { station2pop.draggable.enable();  }
    }
    reclassify();
}

map.on('click', function(pos) { openStat(pos.latlng, "Main Station"); });

openStat(L.latLng(48.00199, 7.81989), "Freiburg im Breisgau, Bissierstr.");
openStat(L.latLng(48.00223, 7.82006), "Freiburg Bissierstraße");