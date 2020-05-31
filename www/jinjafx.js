var loaded = false;
var dirty = false;
var sobj = undefined;
var fe = undefined;
var tid = 0;
var dt = {};
var qs = {};

function jinjafx(method) {
  sobj.innerHTML = "";

  if (window.cmData.getValue().trim().length !== 0) {
    if (!window.cmData.getValue().match(/\w.*[\r\n]+.*\w/)) { 
      window.cmData.focus();
      set_status("darkred", "ERROR", "Not Enough Rows in Data");
      return false;
    }
  }

  if (window.cmTemplate.getValue().length === 0) {
    window.cmTemplate.focus();
    set_status("darkred", "ERROR", "No Template");
    return false;
  }

  fe.focus();

  dt.data = window.cmData.getValue().replace(/^[ \t]+/gm, function(m) {
    var ns = ((m.match(/\t/g) || []).length * 2) + (m.match(/ /g) || []).length;
    return Array(ns + 1).join(" ");
  });
  dt.template = window.cmTemplate.getValue().replace(/\t/g, "  ");
  dt.vars = window.cmVars.getValue().replace(/\t/g, "  ");

  if ((method === "generate") || (method === "get_link")) {
    try {
      dt.data = window.btoa(dt.data);
      dt.template = window.btoa(dt.template);
      dt.vars = window.btoa(dt.vars);

      if (method === "generate") {
        window.open("output.html", "_blank");
      }
      else {
        var xHR = new XMLHttpRequest();
        xHR.open("POST", "get_link", true);

        xHR.onload = function() {
          if (this.status === 200) {
            window.removeEventListener('beforeunload', onBeforeUnload);
            window.location.href = window.location.pathname + "?dt=" + this.responseText;
          }
          else {
            set_status("darkred", "HTTP ERROR " + this.status, this.statusText);
          }
        };

        xHR.onerror = function() {
          set_status("darkred", "ERROR", "XMLHttpRequest.onError()");
        };

        xHR.setRequestHeader("Content-Type", "application/json");
        xHR.send(JSON.stringify(dt));
      }
    }
    catch (ex) {
      set_status("darkred", "ERROR", "Invalid Character Encoding in DataTemplate");
    }
  }
  else if (method === "export") {
    window.open("dt.html", "_blank");
  }
}

window.onload = function() {
  if (typeof window.btoa == 'function') {
    sobj = document.getElementById("status");

    window.onresize = function() {
      document.getElementById("content").style.height = (window.innerHeight - 155) + "px";
    };

    window.onresize();

    document.body.style.display = "block";
    
    var gExtraKeys = {
      "Alt-F": "findPersistent",
      "Ctrl-F": "findPersistent",
      "Cmd-F": "findPersistent",
      "Ctrl-D": false
    };

    CodeMirror.defineMode("data", cmDataMode);    
    window.cmData = CodeMirror.fromTextArea(data, {
      tabSize: 2,
      scrollbarStyle: "null",
      styleSelectedText: true,
      extraKeys: gExtraKeys,
      mode: "data",
      smartIndent: false
    });

    window.cmVars = CodeMirror.fromTextArea(vars, {
      tabSize: 2,
      scrollbarStyle: "null",
      styleSelectedText: true,
      extraKeys: gExtraKeys,
      mode: "yaml",
      smartIndent: false
    });

    window.cmTemplate = CodeMirror.fromTextArea(template, {
      lineNumbers: true,
      tabSize: 2,
      autofocus: true,
      scrollbarStyle: "null",
      styleSelectedText: true,
      extraKeys: gExtraKeys,
      mode: "jinja2",
      smartIndent: false
    });

    fe = window.cmTemplate;
    window.cmData.on("focus", function() { fe = window.cmData });
    window.cmVars.on("focus", function() { fe = window.cmVars });
    window.cmTemplate.on("focus", function() { fe = window.cmTemplate });

    window.cmData.on("blur", onDataBlur);
    document.getElementById("csv").onclick = function() {
      window.cmData.getWrapperElement().style.display = 'block';
      document.getElementById("csv").style.display = 'none';
      window.cmData.focus()
    };
    
    window.cmData.on("beforeChange", onPaste);
    window.cmTemplate.on("beforeChange", onPaste);
    window.cmVars.on("beforeChange", onPaste);

    window.cmData.on("change", onChange);
    window.cmVars.on("change", onChange);
    window.cmTemplate.on("change", onChange);

    Split(["#cdata", "#cvars"], {
      direction: "horizontal",
      cursor: "col-resize",
      sizes: [75, 25],
      snapOffset: 0,
      minSize: 100
    });

    Split(["#top", "#ctemplate"], {
      direction: "vertical",
      cursor: "row-resize",
      sizes: [30, 70],
      snapOffset: 0,
      minSize: 100
    });

    if (window.location.href.indexOf('?') > -1) {
      var v = window.location.href.substr(window.location.href.indexOf('?') + 1).split('&');

      for (var i = 0; i < v.length; i++) {
        var p = v[i].split('=');
        qs[p[0].toLowerCase()] = decodeURIComponent(p.length > 1 ? p[1] : '');
      }

      try {
        if (qs.hasOwnProperty('dt')) {
          var xHR = new XMLHttpRequest();
          xHR.open("GET", "dt/" + qs.dt, true);

          xHR.onload = function() {
            if (this.status === 200) {
              try {
                var dt = JSON.parse(this.responseText);
                dt.data = dt.hasOwnProperty('data') ? window.atob(dt.data) : '';
                dt.template = dt.hasOwnProperty('template') ? window.atob(dt.template) : '';
                dt.vars = dt.hasOwnProperty('vars') ? window.atob(dt.vars) : '';
                load_datatemplate(dt, qs);
              }
              catch (e) {
                set_status("darkred", "INTERNAL ERROR", e);
              }
            }
            else {
              set_status("darkred", "HTTP ERROR " + this.status, this.statusText);
            }
            loaded = true;
          };

          xHR.onerror = function() {
            set_status("darkred", "ERROR", "XMLHttpRequest.onError()");
            loaded = true;
          };
          xHR.send(null);
        }
        else {
          update_from_qs();
          loaded = true;
        }
      }
      catch (ex) {
        set_status("darkred", "ERROR", ex);
        loaded = true; onChange(true);
      }
      if (fe != window.cmData) {
        onDataBlur();
      }
    }
    else {
      loaded = true;
    }
  }
  else {
    document.body.innerHTML = "<p style=\"padding: 15px;\">Sorry, a Modern Browser is Required (Chrome, Firefox, Safari or IE >= 10)</p>";
    document.body.style.display = "block";
  }
};

function quote(str) {
  str = str.replace(/&/g, "&amp;");
  str = str.replace(/>/g, "&gt;");
  str = str.replace(/</g, "&lt;");
  str = str.replace(/"/g, "&quot;");
  str = str.replace(/'/g, "&apos;");
  return str;
}

function escapeRegExp(s) {
  return s.replace(/[\\^$.*+?()[\]{}|]/g, '\\$&');
}

function reset_dt() {
  dt = {};
}

function get_csv_astable() {
  var datarows = window.cmData.getValue().trim().split(/\r?\n/);
  var tc = (datarows[0].match(/\t/g) || []).length;
  var cc = (datarows[0].match(/,/g) || []).length;
  var delim = new RegExp(cc > tc ? '[ \\t]*,[ \\t]*' : ' *\\t *');
  var hrow = datarows[0].split(delim);

  var table = '<table class="table table-condensed">';
  table += '<thead><tr>';
  for (var col = 0; col < hrow.length; col++) {
    table += '<th>' + quote(hrow[col]) + '</th>';
  }
  table += '</tr></thead><tbody>';

  for (var row = 1; row < datarows.length; row++) {
    if (datarows[row].match(/\S/)) {
      var rowdata = datarows[row].split(delim);

      table += '<tr>';
      for (var col = 0; col < hrow.length; col++) {
        table += '<td>' + ((col < rowdata.length) ? quote(rowdata[col]) : '') + '</td>';
      }
      table += '</tr>';
    }
  }
  table += '</tbody></table>';
  return table;
}

function onDataBlur() {
  if (window.cmData.getValue().match(/\w.*[\r\n]+.*\w/)) {
    document.getElementById("csv").innerHTML = get_csv_astable();
    document.getElementById("csv").style.display = 'block';
    window.cmData.getWrapperElement().style.display = 'none';
  }
}

function onPaste(cm, change) {
  if (change.origin === "paste") {
    var _dt = parse_datatemplate(change.text.join('\n'), false);
    if (_dt != null) {
      load_datatemplate(_dt, null);
      change.cancel();
    }
  }
}

function onBeforeUnload(e) {
  e.returnValue = 'Are you sure?';
}

function onChange(errflag) {
  if (loaded) {
    if (!dirty && (errflag !== true)) {
      window.addEventListener('beforeunload', onBeforeUnload);
      dirty = true;
    }
    if (window.location.href.indexOf('?') > -1) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }
}

function load_datatemplate(_dt, _qs) {
  try {
    if (_qs != null) {
      if (_qs.hasOwnProperty("data")) {
        _dt.data = window.atob(_qs.data);
      }
      if (_qs.hasOwnProperty("template")) {
        _dt.template = window.atob(_qs.template);
      }
      if (_qs.hasOwnProperty("vars")) {
        _dt.vars = window.atob(_qs.vars);
      }
    }

    window.cmData.setValue(_dt.hasOwnProperty("data") ? _dt.data : "");
    window.cmTemplate.setValue(_dt.hasOwnProperty("template") ? _dt.template : "");
    window.cmVars.setValue(_dt.hasOwnProperty("vars") ? _dt.vars : "");
    loaded = true;
  }
  catch (ex) {
    set_status("darkred", "ERROR", ex);
    loaded = true; onChange(true);
  }
  if (fe != window.cmData) {
    onDataBlur();
  }
}

function parse_datatemplate(request, us) {
  var _dt = {};

  if (request.match(/<(?:data\.csv|template\.j2|vars\.yml)>/i)) {
    var m = request.match(/<data\.csv>([\s\S]*?)<\/data\.csv>/i);
    if (m != null) {
      _dt.data = m[1].trim();
    }
    m = request.match(/<template\.j2>([\s\S]*?)<\/template\.j2>/i);
    if (m != null) {
      _dt.template = m[1].trim();
    }
    m = request.match(/<vars\.yml>([\s\S]*?)<\/vars\.yml>/i);
    if (m != null) {
      _dt.vars = m[1].trim();
    }
    return _dt;
  }
  else if (us) {
    set_status("darkred", "ERROR", "Invalid DataTemplate Format");
  }
  return null;
}

function update_from_qs() {
  try {
    var _data = qs.hasOwnProperty('data') ? window.atob(qs.data) : null;
    var _template = qs.hasOwnProperty('template') ? window.atob(qs.template) : null;
    var _vars = qs.hasOwnProperty('vars') ? window.atob(qs.vars) : null;

    if (_data != null) {
      window.cmData.setValue(_data);
    }
    if (_template != null) {
      window.cmTemplate.setValue(_template);
    }
    if (_vars != null) {
      window.cmVars.setValue(_vars);
    }
  }
  catch (ex) {
    set_status("darkred", "ERROR", ex);
  }
}

function set_status(color, title, message) {
  clearTimeout(tid);
  tid = setTimeout(function() { sobj.innerHTML = "" }, 5000);
  sobj.style.color = color;
  sobj.innerHTML = "<strong>" + title + "</strong> " + message;
}

function cmDataMode() {
  return {
    startState: function() {
      return { n: 0 };
    },
    token: function(stream, state) {
      if (!state.n && stream.match(/.+/)) {
        state.n = 1;
        return "jfx-header";
      }
      stream.next();
    }
  };
}
