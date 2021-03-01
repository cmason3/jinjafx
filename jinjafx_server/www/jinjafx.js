var loaded = false;
var dirty = false;
var sobj = undefined;
var fe = undefined;
var tid = 0;
var dt_id = '';
var dt = {};
var qs = {};
var datasets = {
  'Default': [CodeMirror.Doc('', 'data'), CodeMirror.Doc('', 'yaml')]
};
var current_ds = 'Default';
var action = 0;
var pending_dt = '';

function getStatusText(code) {
  var statusText = {
    400: 'Bad Request',
    403: 'Forbidden',
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

function select_dataset(e) {
  switch_dataset(e.currentTarget.ds_name, true);
}

function switch_dataset(ds, sflag) {
  if (sflag) {
    datasets[current_ds][0] = window.cmData.swapDoc(datasets[ds][0]);
    datasets[current_ds][1] = window.cmVars.swapDoc(datasets[ds][1]);
  }
  else {
    window.cmData.swapDoc(datasets[ds][0]);
    window.cmVars.swapDoc(datasets[ds][1]);
  }
  if (ds != current_ds) {
    document.getElementById('selected_ds').innerHTML = ds;
    current_ds = ds;
    onDataBlur();
  }
  fe.focus();
}

function rebuild_datasets() {
  document.getElementById('datasets').innerHTML = '';

  Object.keys(datasets).forEach(function(ds) {
    var a = document.createElement('a');
    a.classList.add('dropdown-item');
    a.addEventListener('click', select_dataset, false);
    a.href = '#';
    a.ds_name = ds;
    a.innerHTML = ds;
    document.getElementById('datasets').appendChild(a);
  });

  if (Object.keys(datasets).length > 1) {
    document.getElementById('select_ds').disabled = false;
    document.getElementById('delete_ds').disabled = false;
  }
  else {
    document.getElementById('select_ds').disabled = true;
    document.getElementById('delete_ds').disabled = true;
  }
  document.getElementById('selected_ds').innerHTML = current_ds;
}

function delete_dataset(ds) {
  delete datasets[ds];
  window.addEventListener('beforeunload', onBeforeUnload);
  if (document.getElementById('get_link').value != 'false') {
    document.title = 'JinjaFx [unsaved]';
  }
  dirty = true;

  rebuild_datasets();
  switch_dataset(Object.keys(datasets)[0], false);
  fe.focus();
}

function jinjafx(method) {
  sobj.innerHTML = "";

  if (method == "delete_dataset") {
    if (window.cmData.getValue().match(/\S/) || window.cmVars.getValue().match(/\S/)) {
      action = 1;
      $("#confirm_dialog").modal("show");
      return false;
    }
    delete_dataset(current_ds);
    return false;
  }
  else if (method == "add_dataset") {
    document.getElementById("ds_name").value = '';
    $("#dataset_input").modal("show");
    return false;
  }

  if (window.cmTemplate.getValue().length === 0) {
    window.cmTemplate.focus();
    set_status("darkred", "ERROR", "No Template");
    return false;
  }

  dt = {};

  try {
    if (method === "generate") {
      dt.data = window.cmData.getValue().split(/\r?\n/).filter(function(e) {
        return !e.match(/^[ \t]*#/) && e.match(/\S/);
      });

      if (dt.data.length == 1) {
        window.cmData.focus();
        set_status("darkred", "ERROR", "Not Enough Data Rows");
        return false;
      }

      dt.data = window.btoa(dt.data.join("\n"));
      dt.vars = window.cmVars.getValue().replace(/\t/g, "  ");
      var vaulted_vars = dt.vars.indexOf('$ANSIBLE_VAULT;') > -1;
      dt.vars = window.btoa(dt.vars);
      dt.template = window.btoa(window.cmTemplate.getValue().replace(/\t/g, "  "));
      dt.id = dt_id;
      dt.dataset = current_ds;

      if (vaulted_vars) {
        $("#vault_input").modal("show");
      }
      else {
        if (dt_id != '') {
          window.open("output.html?dt=" + dt_id, "_blank");
        }
        else {
          window.open("output.html", "_blank");
        }
      }
    }
    else if ((method === "export") || (method === "get_link") || (method === "update_link")) {
      dt.template = window.btoa(window.cmTemplate.getValue().replace(/\t/g, "  "));

      if ((current_ds === 'Default') && (Object.keys(datasets).length === 1)) {
        dt.vars = window.btoa(window.cmVars.getValue().replace(/\t/g, "  "));
        dt.data = window.btoa(window.cmData.getValue().split(/\r?\n/).filter(function(e) {
          return !e.match(/^[ \t]*#/) && e.match(/\S/);
        }).join("\n"));
      }
      else {
        dt.datasets = {};
        switch_dataset(current_ds, true);
        Object.keys(datasets).forEach(function(ds) {
          dt.datasets[ds] = {};
          dt.datasets[ds].data = window.btoa(datasets[ds][0].getValue().split(/\r?\n/).filter(function(e) {
            return !e.match(/^[ \t]*#/) && e.match(/\S/);
          }).join("\n"));
          dt.datasets[ds].vars = window.btoa(datasets[ds][1].getValue().replace(/\t/g, "  "));
        });
      }

      if (method === "export") {
        if (dt_id != '') {
          window.open("dt.html?dt=" + dt_id, "_blank");
        }
        else {
          window.open("dt.html", "_blank");
        }
      }
      else {
        set_wait();
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
            }
            else {
              window.removeEventListener('beforeunload', onBeforeUnload);
              window.location.href = window.location.pathname + "?dt=" + this.responseText;
            }
            document.title = 'JinjaFx';
            dirty = false;
            clear_wait();
          }
          else {
            var sT = (this.statusText.length == 0) ? getStatusText(this.status) : this.statusText;
            set_status("darkred", "HTTP ERROR " + this.status, sT);
            clear_wait();
          }
        };

        xHR.onerror = function() {
          set_status("darkred", "ERROR", "XMLHttpRequest.onError()");
          clear_wait();
        };
        xHR.ontimeout = function() {
          set_status("darkred", "ERROR", "XMLHttpRequest.onTimeout()");
          clear_wait();
        };

        xHR.timeout = 10000;
        xHR.setRequestHeader("Content-Type", "application/json");
        xHR.send(JSON.stringify(dt));
      }
    }
  }
  catch (ex) {
    set_status("darkred", "ERROR", "Invalid Character Encoding in DataTemplate");
    clear_wait();
  }
}

window.onload = function() {
  if (typeof window.btoa == 'function') {
    sobj = document.getElementById("status");

    window.onresize = function() {
      document.getElementById("content").style.height = (window.innerHeight - 155) + "px";
    };

    window.onresize();

    if (document.getElementById('get_link').value == 'false') {
      document.getElementById('get').disabled = true;
    }

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
      document.getElementById("ldata").style.display = 'block';
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
      sizes: [60, 40],
      snapOffset: 0,
      minSize: 45
    });

    var vsplit = Split(["#top", "#ctemplate"], {
      direction: "vertical",
      cursor: "row-resize",
      sizes: [30, 70],
      snapOffset: 0,
      minSize: 30
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
      onDataBlur();
    };

    document.getElementById('ltemplate').onclick = function() {
      vsplit.setSizes([0, 100]);
      window.cmTemplate.focus();
      onDataBlur();
    };

    $('#vault_input').on('shown.bs.modal', function() {
      document.getElementById("vault").focus();
    });

    $('#dataset_input').on('shown.bs.modal', function() {
      document.getElementById("ds_name").focus();
    });

    document.getElementById('ml-vault-ok').onclick = function() {
      dt.vault_password = window.btoa(document.getElementById("vault").value);
      window.open("output.html", "_blank");
    };

    document.getElementById('ml-dataset-ok').onclick = function() {
      var new_ds = document.getElementById("ds_name").value;

      if (new_ds.match(/^[A-Z][A-Z0-9_ -]*$/i)) {
        if (!datasets.hasOwnProperty(new_ds)) {
          datasets[new_ds] = [CodeMirror.Doc('', 'data'), CodeMirror.Doc('', 'yaml')];
          rebuild_datasets();
          window.addEventListener('beforeunload', onBeforeUnload);
          if (document.getElementById('get_link').value != 'false') {
            document.title = 'JinjaFx [unsaved]';
          }
          dirty = true;
        }
        switch_dataset(new_ds, true);
      }
      else {
        set_status("darkred", "ERROR", "Invalid Data Set Name");
        fe.focus();
      }
    };

    document.getElementById('ml-confirm-yes').onclick = function() {
      if (action == 1) {
        delete_dataset(current_ds);
      }
      else if (action == 2) {
        apply_dt();
      }
    };

    document.getElementById('vault').onkeyup = function(e) {
      if (e.which == 13) {
        document.getElementById('ml-vault-ok').click();
      }
    };

    document.getElementById('ds_name').onkeyup = function(e) {
      if (e.which == 13) {
        document.getElementById('ml-dataset-ok').click();
      }
    };
    
    if (window.location.href.indexOf('?') > -1) {
      if (document.getElementById('get_link').value != 'false') {
        var v = window.location.href.substr(window.location.href.indexOf('?') + 1).split('&');
  
        for (var i = 0; i < v.length; i++) {
          var p = v[i].split('=');
          qs[p[0].toLowerCase()] = decodeURIComponent(p.length > 1 ? p[1] : '');
        }
  
        try {
          if (qs.hasOwnProperty('dt')) {
            set_wait();
            var xHR = new XMLHttpRequest();
            xHR.open("GET", "dt/" + qs.dt, true);
  
            xHR.onload = function() {
              if (this.status === 200) {
                try {
                  var dt = jsyaml.safeLoad(this.responseText, 'utf8')['dt'];
                  load_datatemplate(dt, qs);
                  dt_id = qs.dt;
  
                  if (this.getResponseHeader('X-Read-Only') == 'true') {
                    document.getElementById('update').disabled = true;
                  }
                  else {
                    document.getElementById('update').disabled = false;
                  }
                  window.history.replaceState({}, document.title, window.location.href.substr(0, window.location.href.indexOf('?')) + '?dt=' + dt_id);
                }
                catch (e) {
                  set_status("darkred", "INTERNAL ERROR", e);
                  window.history.replaceState({}, document.title, window.location.href.substr(0, window.location.href.indexOf('?')));
                }
              }
              else {
                var sT = (this.statusText.length == 0) ? getStatusText(this.status) : this.statusText;
                set_status("darkred", "HTTP ERROR " + this.status, sT);
                window.history.replaceState({}, document.title, window.location.href.substr(0, window.location.href.indexOf('?')));
              }
              loaded = true;
              clear_wait();
            };
  
            xHR.onerror = function() {
              set_status("darkred", "ERROR", "XMLHttpRequest.onError()");
              window.history.replaceState({}, document.title, window.location.href.substr(0, window.location.href.indexOf('?')));
              loaded = true;
              clear_wait();
            };
            xHR.ontimeout = function() {
              set_status("darkred", "ERROR", "XMLHttpRequest.onTimeout()");
              window.history.replaceState({}, document.title, window.location.href.substr(0, window.location.href.indexOf('?')));
              loaded = true;
              clear_wait();
            };

            xHR.timeout = 10000;
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
        set_status("darkred", "HTTP ERROR 503", "Service Unavailable");
        window.history.replaceState({}, document.title, window.location.href.substr(0, window.location.href.indexOf('?')));
        loaded = true;
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

function set_wait() {
  fe.setOption('readOnly', 'nocursor');
  var e = document.getElementById("csv").getElementsByTagName("th");
  for (var i = 0; i < e.length; i++) {
    e[i].style.background = '#eee';
  }
  document.getElementById("csv").style.background = '#eee';
  window.cmData.getWrapperElement().style.background = '#eee';
  window.cmTemplate.getWrapperElement().style.background = '#eee';
  window.cmVars.getWrapperElement().style.background = '#eee';
  document.getElementById('overlay').style.display = 'block';
}

function clear_wait() {
  document.getElementById('overlay').style.display = 'none';
  window.cmVars.getWrapperElement().style.background = '';
  window.cmTemplate.getWrapperElement().style.background = '';
  window.cmData.getWrapperElement().style.background = '';
  document.getElementById("csv").style.background = '#fff';
  var e = document.getElementById("csv").getElementsByTagName("th");
  for (var i = 0; i < e.length; i++) {
    e[i].style.background = 'lightgray';
  }
  fe.setOption('readOnly', false);
  fe.focus();
}

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
      document.getElementById("ldata").style.display = 'none';
      document.getElementById("csv").style.display = 'block';
      window.cmData.getWrapperElement().style.display = 'none';
    }
    else {
      window.cmData.getWrapperElement().style.display = 'block';
      document.getElementById("csv").style.display = 'none';
      document.getElementById("ldata").style.display = 'block';
      window.cmData.refresh();
    }
  }
} 

function apply_dt() {
  load_datatemplate(pending_dt, null);
  if (window.location.href.indexOf('?') > -1) {
    window.history.replaceState({}, document.title, window.location.href.substr(0, window.location.href.indexOf('?')));
  }
  dt_id = '';
  document.getElementById('update').disabled = true;
}

function onPaste(cm, change) {
  if (change.origin === "paste") {
    var t = change.text.join('\n');

    if (t.indexOf('---\ndt:\n') > -1) {
      var obj = jsyaml.safeLoad(t, 'utf8');
      if (obj != null) {
        change.cancel();
        pending_dt = obj['dt'];

        if (dirty) {
          action = 2;
          $("#confirm_dialog").modal("show");
        }
        else {
          apply_dt();
        }
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
      if (document.getElementById('get_link').value != 'false') {
        document.title = 'JinjaFx [unsaved]';
      }
      dirty = true;
    }
  }
}

function load_datatemplate(_dt, _qs) {
  try {
    if (_qs != null) {
      if (_qs.hasOwnProperty("template")) {
        _dt.template = window.atob(_qs.template);
      }
    }

    current_ds = 'Default';

    if (_dt.hasOwnProperty("datasets")) {
      datasets = {};

      Object.keys(_dt.datasets).forEach(function(ds) {
        var data = _dt.datasets[ds].hasOwnProperty("data") ? _dt.datasets[ds].data : "";
        var vars = _dt.datasets[ds].hasOwnProperty("vars") ? _dt.datasets[ds].vars : "";
        datasets[ds] = [CodeMirror.Doc(data, 'data'), CodeMirror.Doc(vars, 'yaml')];
      });

      current_ds = Object.keys(datasets)[0];
      window.cmData.swapDoc(datasets[current_ds][0]);
      window.cmVars.swapDoc(datasets[current_ds][1]);
    }
    else {
      datasets = {
        'Default': [CodeMirror.Doc('', 'data'), CodeMirror.Doc('', 'yaml')]
      };

      if (_qs != null) {
        if (_qs.hasOwnProperty("data")) {
          _dt.data = window.atob(_qs.data);
        }
        if (_qs.hasOwnProperty("vars")) {
          _dt.vars = window.atob(_qs.vars);
        }
      }

      datasets['Default'][0].setValue(_dt.hasOwnProperty("data") ? _dt.data : "");
      window.cmData.swapDoc(datasets['Default'][0]);
      datasets['Default'][1].setValue(_dt.hasOwnProperty("vars") ? _dt.vars : "");
      window.cmVars.swapDoc(datasets['Default'][1]);
    }
    window.cmTemplate.setValue(_dt.hasOwnProperty("template") ? _dt.template : "");

    window.cmData.getDoc().clearHistory();
    window.cmVars.getDoc().clearHistory();
    window.cmTemplate.getDoc().clearHistory();

    rebuild_datasets();
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
