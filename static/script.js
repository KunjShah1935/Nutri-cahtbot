function sendMessage() {

    let input = document.getElementById("user-input");

    let message = input.value.trim();

    if (message === "") return;

    addMessage(message, "user");

    input.value = "";



    fetch("/ask", {

        method: "POST",

        headers: {

            "Content-Type": "application/x-www-form-urlencoded"

        },

        body: "user_input=" + encodeURIComponent(message)

    })

        .then(response => response.json())

        .then(data => {

            addMessage(data.response, "bot");

        });

}



function addMessage(text, type) {

    let chatBox = document.getElementById("chat-box");

    let div = document.createElement("div");

    div.className = type + "-message";

    div.innerText = text;

    chatBox.appendChild(div);

    chatBox.scrollTop = chatBox.scrollHeight;

}



document.getElementById("user-input")

    .addEventListener("keypress", function (e) {

        if (e.key === "Enter")

            sendMessage();

    });