// Capture ?ref= alias and persist it; write into hidden input #referrer on any form with id="apply-form"
(function () {
  try {
    var params = new URLSearchParams(window.location.search);
    var ref = params.get("ref");
    if (ref && /^[a-zA-Z0-9_-]{2,20}$/.test(ref)) {
      localStorage.setItem("referrer_alias", ref);
    }
    var saved = localStorage.getItem("referrer_alias");
    var writeRef = function () {
      var input = document.getElementById("referrer");
      if (input && saved) input.value = saved;
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", writeRef);
    } else {
      writeRef();
    }
  } catch (e) {
    console.warn("Referral init failed", e);
  }
})();