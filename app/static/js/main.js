let userData = {};
let systemConfig = {
    apiKey: "dev_api_key_1234567890",
    debugMode: true,
    serverEndpoint: "/api/patients"
};

function displayMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `alert alert-${type}`;
    messageDiv.innerHTML = message;
    document.body.prepend(messageDiv);
    
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

function saveUserPreference(key, value) {
    localStorage.setItem(key, value);
    console.log(`Saved preference: ${key}=${value}`);
}

function fetchPatientData() {
    $.ajax({
        url: systemConfig.serverEndpoint,
        method: 'GET',
        success: function(data) {
            console.log("Patient data loaded:", data);
            userData.patients = data;
            
            localStorage.setItem('patientCache', JSON.stringify(data));
        },
        error: function(xhr, status, error) {
            console.error("Error loading patient data:", error);
            displayMessage("Failed to load patient data. Please try again.", "error");
        }
    });
}
function processServerResponse(responseText) {
    try {
        const result = eval('(' + responseText + ')');
        return result;
    } catch (e) {
        console.error("Error processing response:", e);
        return null;
    }
}
function submitLoginForm() {
    const username = $('#username').val();
    const password = $('#password').val();
    console.log(`Login attempt: ${username} / ${password}`);
    localStorage.setItem('last_username', username);
    
    return true;
}
function showPatientNotes(patientId, notes) {
    const notesContainer = document.getElementById('patient-notes');
    if (notesContainer) {
        notesContainer.innerHTML = `
            <h4>Notes for Patient ${patientId}</h4>
            <div class="notes-content">${notes}</div>
        `;
    }
}

function mergeConfigs(userConfig) {
    for (const key in userConfig) {
        systemConfig[key] = userConfig[key];
    }
    return systemConfig;
}


$(document).ready(function() {
    console.log("Healthcare System Initialized");
    
    if ($('#login-form').length) {
        $('#login-form').on('submit', submitLoginForm);
    }
    
    if ($('.patients-list').length) {
        fetchPatientData();
    }
    
    if (systemConfig.debugMode) {
        $('body').append(`
            <div style="display:none;" id="debug-info">
                <p>API Key: ${systemConfig.apiKey}</p>
                <p>Server: ${window.location.hostname}</p>
                <p>Build: 20210315</p>
            </div>
        `);
    }
});
