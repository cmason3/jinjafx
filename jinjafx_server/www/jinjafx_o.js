(function() {
  var obj = null;
  var tid = 0;
  var qs = '';
  
  function set_status(color, title, message) {
    clearTimeout(tid);
    tid = setTimeout(function() { sobj.innerHTML = "" }, 5000);
    sobj.style.color = color;
    sobj.innerHTML = "<strong>" + title + "</strong> " + message;
  }
  
  window.onload = function() {
    if (window.opener != null) {
      var dt = window.opener.dt;
      window.opener.reset_dt();

      dayjs.extend(window.dayjs_plugin_advancedFormat);
  
      sobj = document.getElementById("ostatus");

      document.getElementById('copy').onclick = function() {
        sobj.innerHTML = '';
        try {
          var t = document.getElementById('t_' + document.querySelector('.tab-content > .active').getAttribute('id'));

          if (t.nodeName == 'IFRAME') {
            t.contentDocument.designMode = "on";
            t.contentDocument.execCommand("selectAll", false, null);
            t.contentDocument.execCommand("copy", false, null);
            t.contentDocument.designMode = "off";
            t.contentDocument.getSelection().removeAllRanges();
          }
          else {
            var oss = t.selectionStart;
            var ose = t.selectionEnd;
            var ost = t.scrollTop;
            t.focus();
            t.setSelectionRange(0, t.value.length);
            document.execCommand("copy", false, null);
            t.setSelectionRange(oss, ose);
            t.scrollTop = ost;
          }
          set_status("green", "OK", "Copied to Clipboard");
        }
        catch (e) {
          console.log(e);
          set_status("darkred", "ERROR", e);
        }
      };

      document.getElementById('download').onclick = function() {
        sobj.innerHTML = '';
        if (obj != null) {
          var xHR = new XMLHttpRequest();
          xHR.open("POST", 'download' + qs, true);

          xHR.onload = function() {
            if (this.status === 200) {
              var link = document.createElement('a');
              link.href = window.URL.createObjectURL(xHR.response);
              link.download = xHR.getResponseHeader("X-Download-Filename");
              link.click();
            }
          };
          xHR.responseType = "blob";
          xHR.setRequestHeader("Content-Type", "application/json");

          var rd = JSON.stringify(obj.outputs);
          if (rd.length > 1024) {
            xHR.setRequestHeader("Content-Encoding", "gzip");
            xHR.send(pako.gzip(rd));
          }
          else {
            xHR.send(rd);
          }
        }
        var t = document.getElementById('t_' + document.querySelector('.tab-content > .active').getAttribute('id'));
        t.focus();
      };

      if (Object.keys(dt).length !== 0) {
        var _qs = [];
        if (dt.id != '') {
          _qs.push('dt=' + dt.id);
        }
        if (dt.dataset != '') {
          _qs.push('ds=' + dt.dataset);
        }
        qs = (_qs.length > 0) ? '?' + _qs.join('&') : '';
  
        var xHR = new XMLHttpRequest();
        xHR.open("POST", 'jinjafx' + qs, true);
  
        xHR.onload = function() {
          if (this.status === 200) {
            try {
              obj = JSON.parse(xHR.responseText);
              if (obj.status === "ok") {
                var stderr = null;

                if (obj.outputs.hasOwnProperty('_stderr_')) {
                  stderr = window.atob(obj.outputs['_stderr_']);
                  delete (obj.outputs['_stderr_']);
                }

                var oc = Object.keys(obj.outputs).length;
                var oid = 1;
  
                var links = '';
                var tabs = '';
  
                Object.keys(obj.outputs).sort(function(a, b) {
                  if (a == 'Output') {
                    return -1;
                  }
                  return a > b ? 1 : b > a ? -1 : 0;
                }).forEach(function(output) {
                  var g = window.opener.quote(output)
  
                  tabs += '<div id="o' + oid + '" class="h-100 tab-pane fade' + ((oid == 1) ? ' show active' : '') + '">';
                  tabs += '<h4 class="fw-bold">' + g + '</h4>';
  
                  var tc = window.atob(obj.outputs[output]);
                  if (tc.match(/<html.*?>[\s\S]+<\/html>/i)) {
                    tabs += '<iframe id="t_o' + oid + '" class="output" srcdoc="' + tc.replace(/"/g, "&quot;") + '"></iframe>';
                  }
                  else {
                    tabs += '<textarea id="t_o' + oid + '" class="output" readonly>' + window.opener.quote(tc) + '</textarea>';
                  }
  
                  tabs += '</div>';
  
                  links += '<li class="nav-item">';
                  links += '<a class="nav-link' + ((oid == 1) ? ' active"' : '"') + ' data-bs-toggle="tab" href="#o' + oid + '">' + g + '</a>';
                  links += '</li>';
  
                  oid += 1;
                });
  
                document.body.style.display = 'none';
                document.getElementById('status').style.display = 'none';
                document.getElementById('summary').innerHTML = 'Generated at ' + dayjs().format('HH:mm') + ' on ' + dayjs().format('Do MMMM YYYY') + '<br />in ' + Math.ceil(obj.elapsed).toLocaleString() + ' milliseconds';
                document.getElementById('tabs').innerHTML = tabs;
                document.getElementById('nav-links').innerHTML = links;
                document.getElementById('wrap').classList.remove('d-none');
                document.getElementById('footer').classList.remove('d-none');
  
                document.title = 'Outputs' + ((dt.dataset != 'Default') ? ' (' + dt.dataset + ')' : '');
  
                if (oc > 1) {
                  document.getElementById('pills').classList.remove('d-none');
                }
  
                window.onresize = function() {
                  document.getElementById("row").style.height = (window.innerHeight - 200) + "px";
                };
  
                window.onresize();
                document.body.style.display = 'block';

                if (stderr != null) {
                  var html = '<ul class="mb-0">'
                  stderr.trim().split(/\n+/).forEach(function(w) {
                    if (html.match(/<li>/)) {
                      html += '<br />';
                    }
                    html += '<li>' + window.opener.quote(w) + '</li>';
                  });
                  html += '</ul>'

                  document.getElementById('warnings').innerHTML = html;
                  new bootstrap.Modal(document.getElementById('warning_modal'), {
                    keyboard: true
                  }).show();
                }
              }
              else {
                document.title = "Error";
                document.body.innerHTML = "<div id=\"status\" class=\"alert alert-danger\"><strong><h4>JinjaFx Error</h4></strong><pre>"+ obj.error + "</pre></div>";
              }
            }
            catch (e) {
              console.log(e);
              document.title = "Error";
              document.body.innerHTML = "<div id=\"status\" class=\"alert alert-danger\"><strong><h4>Internal Error</h4></strong>" + e + "</div>";
            }
          }
          else {
            document.title = "Error";
            var sT = (this.statusText.length == 0) ? window.opener.getStatusText(this.status) : this.statusText;
            document.body.innerHTML = "<div id=\"status\" class=\"alert alert-danger\"><strong><h4>HTTP ERROR " + this.status + "</h4></strong>"+ sT + "</div>";
          }
        };
        xHR.timeout = 0;
        xHR.onerror = function() {
          document.title = "Error";
          document.body.innerHTML = "<div id=\"status\" class=\"alert alert-danger\"><strong><h4>JinjaFx Error</h4></strong>XMLHttpRequest.onError()</div>";
        };
        xHR.setRequestHeader("Content-Type", "application/json");
        
        var rd = JSON.stringify(dt);
        if (rd.length > 1024) {
          xHR.setRequestHeader("Content-Encoding", "gzip");
          xHR.send(pako.gzip(rd));
        }
        else {
          xHR.send(rd);
        }
      }
      else {
        document.title = "Error";
        document.body.innerHTML = "<div id=\"status\" class=\"alert alert-danger\"><strong><h4>JinjaFx Error</h4></strong>DataTemplate Expired</div>";
      }
    }
    else {
      document.title = "Error";
      document.body.innerHTML = "<div id=\"status\" class=\"alert alert-danger\"><strong><h4>JinjaFx Error</h4></strong>DataTemplate Expired</div>";
    }
  };
})();
