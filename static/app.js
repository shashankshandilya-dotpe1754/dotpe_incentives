(function () {
  const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
  const form = document.getElementById('salForm');
  const inputs = Array.from(document.querySelectorAll('input.sal'));
  const qsum = document.getElementById('qsum');
  const status = document.getElementById('status');
  const btn = document.getElementById('saveBtn');

  function updateSum() {
    if (!qsum) return;
    const t = inputs.reduce((a, i) => a + (Number(i.value) > 0 ? Number(i.value) : 0), 0);
    qsum.textContent = inr.format(t);
  }
  inputs.forEach(i => i.addEventListener('input', updateSum));
  updateSum();

  function setStatus(msg, kind) {
    status.textContent = msg;
    status.className = 'status' + (kind ? ' ' + kind : '');
  }

  if (form && btn) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      btn.disabled = true;
      btn.textContent = 'Saving…';
      setStatus('');
      try {
        const res = await fetch(form.dataset.url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': form.dataset.csrf },
          body: JSON.stringify({ salaries: inputs.map(i => i.value.trim()) }),
          credentials: 'same-origin',
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || 'Your salary couldn’t be saved. Try again.');
        window.location.assign('/?saved=1');
      } catch (err) {
        setStatus(err.message, 'err');
        btn.disabled = false;
        btn.textContent = 'Save and recalculate';
      }
    });
  }

  // "100% live" / "Below 100% live" tabs
  const tabs = Array.from(document.querySelectorAll('.seg [role="tab"]'));
  function select(tab) {
    tabs.forEach(t => {
      const on = t === tab;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
    });
  }
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => select(t));
    t.addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
      select(next);
      next.focus();
    });
  });
})();
