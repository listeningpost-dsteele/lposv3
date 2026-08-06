(function () {
  var input = document.getElementById('search-input');
  var results = document.getElementById('search-results');
  if (!input || !results) return;
  var prefix = document.body.getAttribute('data-root') || '';
  var index = null;

  function load(cb) {
    if (index) return cb(index);
    var xhr = new XMLHttpRequest();
    xhr.open('GET', prefix + 'search-index.json');
    xhr.onload = function () {
      try { index = JSON.parse(xhr.responseText); } catch (e) { index = []; }
      cb(index);
    };
    xhr.onerror = function () { cb([]); };
    xhr.send();
  }

  function search(q) {
    q = q.toLowerCase().trim();
    if (!q) { results.style.display = 'none'; results.innerHTML = ''; return; }
    load(function (pages) {
      var terms = q.split(/\s+/);
      var scored = [];
      for (var i = 0; i < pages.length; i++) {
        var p = pages[i];
        var title = p.title.toLowerCase();
        var text = p.text.toLowerCase();
        var score = 0, ok = true;
        for (var t = 0; t < terms.length; t++) {
          var term = terms[t];
          if (title.indexOf(term) !== -1) { score += 10; }
          else if (text.indexOf(term) !== -1) { score += 1; }
          else { ok = false; break; }
        }
        if (ok) scored.push([score, p]);
      }
      scored.sort(function (a, b) { return b[0] - a[0]; });
      results.innerHTML = '';
      var top = scored.slice(0, 12);
      for (var j = 0; j < top.length; j++) {
        var page = top[j][1];
        var a = document.createElement('a');
        a.href = prefix + page.url;
        a.textContent = page.title;
        var small = document.createElement('small');
        small.textContent = page.section;
        a.appendChild(small);
        results.appendChild(a);
      }
      results.style.display = top.length ? 'block' : 'none';
    });
  }

  input.addEventListener('input', function () { search(input.value); });
  input.addEventListener('focus', function () { if (input.value) search(input.value); });
  document.addEventListener('click', function (ev) {
    if (!results.contains(ev.target) && ev.target !== input) {
      results.style.display = 'none';
    }
  });
})();
