var loaded = false;
var dirty = false;
var sobj = undefined;
var fe = undefined;
var tid = 0;
var dt_id = '';
var dt = {};
var qs = {};

function getStatusText(code) {
  var statusText = {
    400: 'Bad Request',
    404: 'Not Found',
    413: 'Request Entity Too Large',
    429: 'Too Many Requests',
    500: 'Internal Server Error',
    503: 'Service Unavailable'
  };

  if (statusText.hasOwnProperty(code)) {
    return statusText[code];
  }
  return '';
}

function jinjafx(method) {
  sobj.innerHTML = "";
  dt = {};

  if (window.cmTemplate.getValue().length === 0) {
    window.cmTemplate.focus();
    set_status("darkred", "ERROR", "No Template");
    return false;
  }

  var datarows = window.cmData.getValue();

  if (method == "generate") {
    datarows = datarows.split(/\r?\n/).filter(function(e) {
      return !e.match(/^[ \t]*#/) && e.match(/\S/);
    });

    if (datarows.length == 1) {
      window.cmData.focus();
      set_status("darkred", "ERROR", "Not Enough Rows in Data");
      return false;
    }
    datarows = datarows.join("\n");
  }

  fe.focus();

  dt.data = datarows;
  dt.template = window.cmTemplate.getValue().replace(/\t/g, "  ");
  dt.vars = window.cmVars.getValue().replace(/\t/g, "  ");

  var alias = "myalias";

  if ((method === "generate") || (method === "get_link") || (method == "update_link")) {
    try {
      var vaulted_vars = dt.vars.indexOf('$ANSIBLE_VAULT;') > -1;

      dt.data = window.btoa(dt.data);
      dt.template = window.btoa(dt.template);
      dt.vars = window.btoa(dt.vars);
      dt.id = dt_id;

      if (method === "generate") {
        if (vaulted_vars) {
          $("#vault_input").modal("show")
        }
        else {
          window.open("output.html", "_blank");
        }
      }
      else {
        var xHR = new XMLHttpRequest();

        if (method == "update_link") {
          xHR.open("POST", "get_link?id=" + dt_id, true);
        }
        else {
          xHR.open("POST", "get_link", true);
        }

        xHR.onload = function() {
          if (this.status === 200) {
            if (method == "update_link") {
              set_status("green", "OK", "Link Updated");
              window.removeEventListener('beforeunload', onBeforeUnload);
              dirty = false;
            }
            else {
              window.removeEventListener('beforeunload', onBeforeUnload);
              window.location.href = window.location.pathname + "?dt=" + this.responseText;
            }
          }
          else {
            var sT = (this.statusText.length == 0) ? getStatusText(this.status) : this.statusText;
            set_status("darkred", "HTTP ERROR " + this.status, sT);
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
      styleSelectedText: false,
      extraKeys: gExtraKeys,
      mode: "data",
      smartIndent: false
    });

    window.cmVars = CodeMirror.fromTextArea(vars, {
      tabSize: 2,
      scrollbarStyle: "null",
      styleSelectedText: false,
      extraKeys: gExtraKeys,
      mode: "yaml",
      smartIndent: false
    });

    window.cmTemplate = CodeMirror.fromTextArea(template, {
      lineNumbers: true,
      tabSize: 2,
      autofocus: true,
      scrollbarStyle: "null",
      styleSelectedText: false,
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
      window.cmData.refresh();
      window.cmData.focus();
    };
    
    window.cmData.on("beforeChange", onPaste);
    window.cmTemplate.on("beforeChange", onPaste);
    window.cmVars.on("beforeChange", onPaste);

    window.cmData.on("change", onChange);
    window.cmVars.on("change", onChange);
    window.cmTemplate.on("change", onChange);

    var hsplit = Split(["#cdata", "#cvars"], {
      direction: "horizontal",
      cursor: "col-resize",
      sizes: [75, 25],
      snapOffset: 0,
      minSize: 50 
    });

    var vsplit = Split(["#top", "#ctemplate"], {
      direction: "vertical",
      cursor: "row-resize",
      sizes: [30, 70],
      snapOffset: 0,
      minSize: 130
    });

    document.getElementById('ldata').onclick = function() {
      hsplit.setSizes([100, 0]);
      vsplit.setSizes([100, 0]);
      window.cmData.focus();
    };

    document.getElementById('lvars').onclick = function() {
      hsplit.setSizes([0, 100]);
      vsplit.setSizes([100, 0]);
      window.cmVars.focus();
    };

    document.getElementById('ltemplate').onclick = function() {
      vsplit.setSizes([0, 100]);
      window.cmTemplate.focus();
    };

    $('#vault_input').on('shown.bs.modal', function() {
      document.getElementById("vault").focus();
    });

    document.getElementById('ml-ok').onclick = function() {
      dt.vault_password = window.btoa(document.getElementById("vault").value);
      window.open("output.html", "_blank");
    };

    document.getElementById('vault').onkeyup = function(e) {
      if (e.which == 13) {
        document.getElementById('ml-ok').click();
      }
    };

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
                var dt = jsyaml.safeLoad(this.responseText, 'utf8')['dt'];
                load_datatemplate(dt, qs);
                dt_id = qs.dt;
                document.getElementById('update').disabled = false;
              }
              catch (e) {
                set_status("darkred", "INTERNAL ERROR", e);
                window.history.replaceState({}, document.title, window.location.pathname);
              }
            }
            else {
              var sT = (this.statusText.length == 0) ? getStatusText(this.status) : this.statusText;
              set_status("darkred", "HTTP ERROR " + this.status, sT);
              window.history.replaceState({}, document.title, window.location.pathname);
            }
            loaded = true;
          };

          xHR.onerror = function() {
            set_status("darkred", "ERROR", "XMLHttpRequest.onError()");
            window.history.replaceState({}, document.title, window.location.pathname);
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

function get_csv_astable(datarows) {
  var tc = (datarows[0].match(/\t/g) || []).length;
  var cc = (datarows[0].match(/,/g) || []).length;
  var delim = new RegExp(cc > tc ? '[ \\t]*,[ \\t]*' : ' *\\t *');
  var hrow = datarows[0].split(delim);

  var table = '<table class="table table-sm">';
  table += '<thead><tr class="table-secondary">';
  for (var col = 0; col < hrow.length; col++) {
    table += '<th>' + quote(hrow[col]) + '</th>';
  }
  table += '</tr></thead><tbody>';

  for (var row = 1; row < datarows.length; row++) {
    var rowdata = datarows[row].split(delim);

    table += '<tr>';
    for (var col = 0; col < hrow.length; col++) {
      table += '<td>' + ((col < rowdata.length) ? quote(rowdata[col]) : '') + '</td>';
    }
    table += '</tr>';
  }
  table += '</tbody></table>';
  return table;
}

function onDataBlur(cm, evt) {
  if ((evt == null) || ((evt.relatedTarget != null) && (evt.relatedTarget.tagName != 'INPUT'))) {
    var datarows = window.cmData.getValue().trim().split(/\r?\n/).filter(function(e) {
      return !e.match(/^[ \t]*#/) && e.match(/\S/);
    });
    if (datarows.length > 1) {
      document.getElementById("csv").innerHTML = get_csv_astable(datarows);
      document.getElementById("csv").style.display = 'block';
      window.cmData.getWrapperElement().style.display = 'none';
    }
  }
} 

function onPaste(cm, change) {
  if (change.origin === "paste") {
    var t = change.text.join('\n');

    if (t.indexOf('---\ndt:\n') > -1) {
      var obj = jsyaml.safeLoad(t, 'utf8');
      if (obj != null) {
        load_datatemplate(obj['dt'], null);
        change.cancel();

        if (window.location.href.indexOf('?') > -1) {
          window.history.replaceState({}, document.title, window.location.pathname);
        }
        dt_id = '';
        document.getElementById('update').disabled = true;
      }
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
      if (stream.sol() && stream.match(/[ \t]*#/)) {
        stream.skipToEnd();
        return "comment";
      }
      if (!state.n && stream.sol() && stream.match(/[ \t]*\S/)) {
        state.n = 1;
        stream.skipToEnd();
        return "jfx-header";
      }
      stream.next();
    }
  };
}
