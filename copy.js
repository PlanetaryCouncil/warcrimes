const msg = document.querySelector('.cpmsg');
const copy = async (text, note) => {
  try { await navigator.clipboard.writeText(text); }
  catch { const t = document.createElement('textarea'); t.value = text; document.body.append(t); t.select(); document.execCommand('copy'); t.remove(); }
  msg.textContent = note; clearTimeout(copy.t); copy.t = setTimeout(() => msg.textContent = '', 2500);
};
document.querySelectorAll('button.cp').forEach(b => b.addEventListener('click', () => {
  copy(b.dataset.tweet, 'Copied 1 source'); b.textContent = '✓'; setTimeout(() => b.textContent = '𝕏', 1500);
}));
document.querySelector('button.cpall')?.addEventListener('click', e => {
  const lines = [...document.querySelectorAll('button.cp')].map(b => b.dataset.tweet);
  copy(e.target.dataset.head + '\n\n' + lines.join('\n\n'), `Copied ${lines.length} sources`);
});
