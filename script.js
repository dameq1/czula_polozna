const toggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('.nav');
toggle.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  toggle.setAttribute('aria-expanded', String(open));
  toggle.textContent = open ? '×' : '☰';
  toggle.setAttribute('aria-label', open ? 'Zamknij menu' : 'Otwórz menu');
});
nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  nav.classList.remove('open');
  toggle.setAttribute('aria-expanded', 'false');
  toggle.textContent = '☰';
  toggle.setAttribute('aria-label', 'Otwórz menu');
}));
document.getElementById('year').textContent = new Date().getFullYear();

// Link „Umów…” na karcie usługi od razu wybiera tę usługę w formularzu.
document.querySelectorAll('[data-topic]').forEach(link => link.addEventListener('click', () => {
  const select = document.getElementById('topic');
  const wanted = link.dataset.topic;
  const option = Array.from(select.options).find(o => o.value === wanted || o.text === wanted);
  if (option) select.value = option.value;
}));

const contactForm = document.getElementById('contact-form');
const contactFields = document.getElementById('contact-form-fields');
const messageResult = document.getElementById('message-result');
const preparedMessage = document.getElementById('prepared-message');
const preparedTo = document.getElementById('prepared-to');
const preparedSubject = document.getElementById('prepared-subject');
const copyStatus = document.getElementById('copy-status');

let currentEmail = '';
let currentSubject = '';
let currentBody = '';
let currentFullText = '';

const phoneField = contactForm.elements.phone;
const emailField = contactForm.elements.email;
function validateContactMethod() {
  const missingBoth = !phoneField.value.trim() && !emailField.value.trim();
  const message = missingBoth ? 'Podaj numer telefonu lub adres e-mail, żebym mogła odpowiedzieć.' : '';
  phoneField.setCustomValidity(message);
  emailField.setCustomValidity(message);
}
phoneField.addEventListener('input', validateContactMethod);
emailField.addEventListener('input', validateContactMethod);

contactForm.addEventListener('submit', event => {
  event.preventDefault();
  validateContactMethod();
  if (!contactForm.reportValidity()) return;

  const name = contactForm.elements.name.value.trim();
  const phone = contactForm.elements.phone.value.trim();
  const email = contactForm.elements.email.value.trim();
  const city = contactForm.elements.city.value.trim();
  const topic = contactForm.elements.topic.value;
  const preferredContact = contactForm.elements.preferred_contact.value;
  const message = contactForm.elements.message.value.trim();
  const recipient = (contactForm.dataset.recipient || '').trim();

  currentEmail = recipient;
  currentSubject = `Zapytanie ze strony - ${topic}`;
  currentBody = [
    'Dzień dobry,',
    '',
    `Mam na imię ${name}.`,
    `Telefon: ${phone || 'nie podano'}`,
    `Adres e-mail: ${email || 'nie podano'}`,
    `Miejscowość: ${city || 'nie podano'}`,
    `W sprawie: ${topic}`,
    `Preferowany kontakt: ${preferredContact || 'nie wybrano'}`,
    '',
    message || 'Proszę o kontakt i informację o dostępnych terminach.',
    '',
    'Pozdrawiam,',
    name
  ].join('\n');
  currentFullText = `Do: ${recipient}\nTemat: ${currentSubject}\n\n${currentBody}`;

  preparedTo.textContent = recipient || 'Uzupełnij adres e-mail w konfiguracji strony';
  preparedSubject.textContent = currentSubject;
  preparedMessage.value = currentBody;
  copyStatus.textContent = 'Wiadomość jest gotowa. Możesz ją skopiować lub otworzyć w swojej poczcie.';
  contactFields.hidden = true;
  messageResult.hidden = false;
  messageResult.focus();
});

document.getElementById('copy-message').addEventListener('click', async () => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(currentFullText);
    } else {
      const temporary = document.createElement('textarea');
      temporary.value = currentFullText;
      temporary.setAttribute('readonly', '');
      temporary.style.position = 'fixed';
      temporary.style.opacity = '0';
      document.body.appendChild(temporary);
      temporary.select();
      const copied = document.execCommand('copy');
      temporary.remove();
      if (!copied) throw new Error('Kopiowanie niedostępne');
    }
    copyStatus.textContent = 'Skopiowano temat i treść. Wklej je w nowej wiadomości w Gmailu lub innej poczcie.';
  } catch (error) {
    preparedMessage.focus();
    preparedMessage.select();
    copyStatus.textContent = 'Nie udało się skopiować automatycznie. Zaznaczony tekst możesz skopiować skrótem Ctrl+C lub Kopiuj.';
  }
});

document.getElementById('open-gmail').addEventListener('click', () => {
  const gmailUrl = new URL('https://mail.google.com/mail/');
  gmailUrl.searchParams.set('view', 'cm');
  gmailUrl.searchParams.set('fs', '1');
  gmailUrl.searchParams.set('to', currentEmail);
  gmailUrl.searchParams.set('su', currentSubject);
  gmailUrl.searchParams.set('body', currentBody);
  window.open(gmailUrl.toString(), '_blank', 'noopener,noreferrer');
});

document.getElementById('open-mail-app').addEventListener('click', () => {
  const mailto = `mailto:${currentEmail}?subject=${encodeURIComponent(currentSubject)}&body=${encodeURIComponent(currentBody)}`;
  window.location.href = mailto;
});

document.getElementById('edit-message').addEventListener('click', () => {
  messageResult.hidden = true;
  contactFields.hidden = false;
  document.getElementById('name').focus();
});

// Pasek „Zadzwoń” na telefonie chowa się, dopóki widać przyciski w hero (nie dublujemy ich).
const callBar = document.querySelector('.call-bar');
const heroActions = document.querySelector('.hero-actions');
if (callBar && heroActions && 'IntersectionObserver' in window) {
  new IntersectionObserver(([entry]) => {
    callBar.classList.toggle('is-hidden', entry.isIntersecting);
  }).observe(heroActions);
}
