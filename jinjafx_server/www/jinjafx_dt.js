(function() {
  window.onload = function() {
    var dt = window.opener.dt;
    window.opener.reset_dt();

    if (Object.keys(dt).length !== 0) {
      var dtx = '# JinjaFx DataTemplate\n# https://github.com/cmason3/jinjafx\n\n';

      dtx += '---\n';
      dtx += 'dt:\n';

      if (dt.hasOwnProperty('datasets')) {
        dtx += '  datasets:\n';

        Object.keys(dt.datasets).forEach(function(ds) {
          var data = dt.datasets[ds].data.match(/\S/) ? window.atob(dt.datasets[ds].data).replace(/\s+$/g, '') : "";
          var vars = dt.datasets[ds].vars.match(/\S/) ? window.atob(dt.datasets[ds].vars).replace(/\s+$/g, '') : "";

          dtx += '    "' + ds + '":\n';

          if (data == '') {
            dtx += '      data: ""\n\n';
          }
          else {
            dtx += '      data: |2\n';
            dtx += window.opener.quote(data.replace(/^/gm, '        ')) + '\n\n';
          }

          if (vars == '') {
            dtx += '      vars: ""\n\n';
          }
          else {
            dtx += '      vars: |2\n';
            dtx += window.opener.quote(vars.replace(/^/gm, '        ')) + '\n\n';
          }
        });
      }
      else {
        var data = dt.data.match(/\S/) ? window.atob(dt.data).replace(/\s+$/g, '') : "";
        var vars = dt.vars.match(/\S/) ? window.atob(dt.vars).replace(/\s+$/g, '') : "";

        if (data == '') {
          dtx += '  data: ""\n\n';
        }
        else {
          dtx += '  data: |2\n';
          dtx += window.opener.quote(data.replace(/^/gm, '    ')) + '\n\n';
        }

        if (vars == '') {
          dtx += '  vars: ""\n\n';
        }
        else {
          dtx += '  vars: |2\n';
          dtx += window.opener.quote(vars.replace(/^/gm, '    ')) + '\n\n';
        }
      }

      var template = dt.template.match(/\S/) ? window.atob(dt.template).replace(/\s+$/g, '') : "";

      if (template == '') {
        dtx += '  template: ""\n';
      }
      else {
        dtx += '  template: |2\n';
        dtx += window.opener.quote(template.replace(/^/gm, '    ')) + '\n';
      }

      document.body.innerHTML = "<pre>" + dtx + "</pre>";
    }
  };
})();
