function getCSRFToken() {
    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');

        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();

            if (cookie.substring(0, 10) === 'csrftoken=') {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }

    return cookieValue;
}

// Toggle function
function toggleTask(taskId) {
    fetch(`/tasks/toggle/${taskId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Network error");
        }
        return response.json();
    })
    .then(data => {
        const statusCell = document.getElementById(`status-${taskId}`);

        if (!statusCell) return;

        statusCell.innerHTML =
            data.status === 'completed'
                ? '<span class="badge bg-success">Completed</span>'
                : '<span class="badge bg-warning text-dark">Pending</span>';
    })
    .catch(error => console.error('Error:', error));
}

// Event delegation
document.addEventListener("DOMContentLoaded", function () {
    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".toggle-btn");

        if (!btn) return;

        const taskId = btn.dataset.id;
        toggleTask(taskId);
    });
});