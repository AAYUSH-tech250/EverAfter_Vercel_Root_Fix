(function () {
  // copy-link buttons + guest-count stepper
  document.addEventListener("click", function (e) {
    var copy = e.target.closest(".copy");
    if (copy) {
      var link = copy.dataset.link;
      var done = function () {
        var old = copy.textContent;
        copy.textContent = "Copied ✓";
        setTimeout(function () { copy.textContent = old; }, 1500);
      };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(link).then(done);
      } else {
        var t = document.createElement("textarea");
        t.value = link; document.body.appendChild(t); t.select();
        document.execCommand("copy"); document.body.removeChild(t); done();
      }
    }
    var step = e.target.closest("[data-step]");
    if (step) {
      var input = step.parentElement.querySelector("input");
      var min = parseInt(input.min || "0", 10), max = parseInt(input.max || "99", 10);
      var val = (parseInt(input.value, 10) || 0) + parseInt(step.dataset.step, 10);
      input.value = Math.min(max, Math.max(min, val));
    }
  });

  // show/hide the travel section depending on the chosen reply
  function applyStatus() {
    var checked = document.querySelector("input[name=status]:checked");
    var v = checked ? checked.value : "";
    document.querySelectorAll("[data-show-for]").forEach(function (el) {
      el.hidden = el.dataset.showFor.split(" ").indexOf(v) === -1;
    });
  }
  document.querySelectorAll("input[name=status]").forEach(function (r) {
    r.addEventListener("change", applyStatus);
  });
  applyStatus();

  // countdown on the invitation page
  var cd = document.getElementById("countdown");
  if (cd && cd.dataset.date) {
    var days = Math.ceil((new Date(cd.dataset.date + "T00:00:00") - new Date()) / 86400000);
    if (days > 0) cd.innerHTML = "<strong>" + days + "</strong><span>day" + (days === 1 ? "" : "s") + " to go</span>";
  }
})();
