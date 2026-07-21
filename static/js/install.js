const bearingCodeInput = document.getElementById('bearingCode');
const verifyMessage = document.getElementById('verifyMessage');
const submitBtn = document.getElementById('submitBtn');
const resultMessage = document.getElementById('resultMessage');

let debounceTimer = null;

// Feature 1: live bearing verification as the mechanic types (debounced so we don't
// fire a request on every single keystroke - we wait 400ms after typing stops)
bearingCodeInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const code = bearingCodeInput.value.trim();
    submitBtn.disabled = true;

    if (!code) {
        verifyMessage.textContent = '';
        return;
    }

    verifyMessage.textContent = 'Checking...';
    verifyMessage.className = 'form-text text-muted';

    debounceTimer = setTimeout(() => {
        fetch('/api/verify-bearing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bearing_code: code })
        })
        .then(res => res.json())
        .then(data => {
            verifyMessage.textContent = data.message;
            verifyMessage.className = data.valid ? 'form-text text-success' : 'form-text text-danger';
            submitBtn.disabled = !data.valid;
        });
    }, 400);
});

// Feature 2/3/5: submit installation via AJAX - mechanic comes from the logged-in session
// on the server side, so we don't send it from the form at all
submitBtn.addEventListener('click', () => {
    const payload = {
        bearing_code: bearingCodeInput.value.trim(),
        location: document.getElementById('location').value.trim()
    };

    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';

    fetch('/api/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        submitBtn.textContent = 'Complete Installation';
        if (data.success) {
            resultMessage.innerHTML = `
                <div class="alert alert-success">
                    Installation recorded. Warranty valid until <strong>${data.warranty_expiry}</strong>.<br>
                    +${data.points_awarded} loyalty points awarded (total: ${data.mechanic_points}).<br>
                    <a href="${data.certificate_url}" class="btn btn-sm btn-primary mt-2">View Certificate</a>
                </div>`;
            bearingCodeInput.value = '';
            verifyMessage.textContent = '';
        } else {
            resultMessage.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
            submitBtn.disabled = false;
        }
    });
});
