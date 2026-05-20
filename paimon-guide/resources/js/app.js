/**
 * Paimon Guide — Chat Logic (Vanilla JS)
 *
 * Handles:
 * - Sending messages to /api/check-quest (Knowledge Base lookup)
 * - Displaying bot and user messages in the chat
 * - Typing indicator / loading state
 * - Error handling
 * - Nickname + avatar persistence via localStorage
 * - Retroactive nickname & avatar updates in chat history
 */

// ============================
// Avatar List (profile_selector folder — 4-column grid)
// ============================
const AVATARS = [
    '/images/profile_selector/Paimon.webp',
    '/images/profile_selector/013a6b4d7197e0ce2407a862a450b44b.webp',
    '/images/profile_selector/0424a279f2ad3453a598ceee6b79e958.webp',
    '/images/profile_selector/0648d477c95f03343b774e965cc82685.webp',
    '/images/profile_selector/07120fa92c4ac2dea2d70c14f3e0a2bc.webp',
    '/images/profile_selector/0b31b63f5bbff7e080a8d4c6d61f96ea.webp',
    '/images/profile_selector/13ae08f2741b0e1d0aeea1359f391439.webp',
    '/images/profile_selector/148efe62afdfcd350f6657289437f5e1.webp',
    '/images/profile_selector/19e5f2545b7362ce9348c089561f20b6.webp',
    '/images/profile_selector/2d422efaa6247bef465456ac095480e6.webp',
    '/images/profile_selector/302b2c185f63cad48736c627a1551afe.webp',
    '/images/profile_selector/375b7f93e634a1cd118fd36f9c71c8d2.webp',
    '/images/profile_selector/395e92bd67e8ff1ff1e89a30791d198c.webp',
    '/images/profile_selector/3ccb6539778c271155041b88211b161f.webp',
    '/images/profile_selector/3d6a3d4905ff6ad525930cd57166ac12.webp',
    '/images/profile_selector/3e895f27b4376be4b3af5cf1b5d43684.webp',
    '/images/profile_selector/3edfdb32912ec3e9fd9e72429735fc6e.webp',
    '/images/profile_selector/4a5b20c6206bcb080c32d537e8242ba7.webp',
    '/images/profile_selector/50d1dc021b3785a9ed026ae4edb64a50.webp',
    '/images/profile_selector/51d1c32dae931062c50d12bce3a35b33.webp',
    '/images/profile_selector/5d86919f27380c89700534e8523af9fb.webp',
    '/images/profile_selector/5f4b0cfda736c28180156cb8b849f948.webp',
    '/images/profile_selector/606b795c50764df61dcea48306c0f2aa.webp',
    '/images/profile_selector/62d00d9c78857a3b0272670df6d43f83.webp',
    '/images/profile_selector/763334ccaca8e595fef3c17076b161b3.webp',
    '/images/profile_selector/78094cdf179deeb236bdd629b12cb140.webp',
    '/images/profile_selector/79bcee2acc7a034f75b0d7be5a1ca557.webp',
    '/images/profile_selector/7a9857e042e77ade601a492d15a5e2f7.webp',
    '/images/profile_selector/7e44a169697132a02a8a02d5fef51e0d.webp',
    '/images/profile_selector/854f967dbf5d8e38fdab9804b065db50.webp',
    '/images/profile_selector/87eb17a99989c90ce2be54fd52549327.webp',
    '/images/profile_selector/8d7528bb86f445a1b5c2224512d5cb42.webp',
    '/images/profile_selector/9093f472d7656013ec39d9add0c32e2d.webp',
    '/images/profile_selector/9d16b2f1f89173db12cb4a23665fe7d6.webp',
    '/images/profile_selector/a1277e42f778e739c70834721ac9b0b9.webp',
    '/images/profile_selector/a4ae1a6659b9f797c2355a78ab1b1456.webp',
    '/images/profile_selector/acc786f26a24b3b816db41129fc0cab4.webp',
    '/images/profile_selector/ae3db9ad714e4247e905058c516a9172.webp',
    '/images/profile_selector/b1d1ba210006f42643b1253075833460.webp',
    '/images/profile_selector/b8c7c4d36b5a2cf9c7cf4bf16787b349.webp',
];

// ============================
// Global Loader Logic
// ============================
window.addEventListener('load', () => {
    const loader = document.getElementById('app-loader');
    if (loader) {
        // Slight delay to ensure the UI is fully painted and the loader animation is visible briefly
        setTimeout(() => {
            loader.classList.add('hidden');
            setTimeout(() => {
                if (loader.parentNode) loader.parentNode.removeChild(loader);
            }, 500); // Matches CSS transition duration
        }, 400);
    }
});

document.addEventListener('DOMContentLoaded', () => {
    // ============================
    // DOM Elements
    // ============================
    const chatMessages = document.getElementById('chat-messages');
    const chatInput    = document.getElementById('chat-input');
    const sendBtn      = document.getElementById('send-btn');
    const nicknameInput = document.getElementById('nickname-input');
    const avatarGrid   = document.getElementById('avatar-grid');

    // ============================
    // State
    // ============================
    let nickname       = localStorage.getItem('paimon_nickname') || 'Traveler';
    let selectedAvatar = parseInt(localStorage.getItem('paimon_avatar') || '0', 10);
    let isProcessing   = false;

    // ============================
    // Build Avatar Grid dynamically
    // ============================
    buildAvatarGrid();

    // ============================
    // Initialization
    // ============================
    nicknameInput.value = nickname;
    highlightAvatar(selectedAvatar);
    showGreeting();

    // ============================
    // Event Listeners
    // ============================
    sendBtn.addEventListener('click', handleSend);

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    nicknameInput.addEventListener('input', (e) => {
        nickname = e.target.value.trim() || 'Traveler';
        localStorage.setItem('paimon_nickname', nickname);
        // Retroactively update all existing user-message sender labels
        updateAllSenderLabels(nickname);
    });

    // ============================
    // Build Avatar Grid
    // ============================
    function buildAvatarGrid() {
        if (!avatarGrid) return;
        avatarGrid.innerHTML = '';

        const COLS = 4;
        const ROWS = Math.ceil(AVATARS.length / COLS);

        for (let row = 0; row < ROWS; row++) {
            const rowEl = document.createElement('div');
            rowEl.className = 'avatar-row';

            for (let col = 0; col < COLS; col++) {
                const idx = row * COLS + col;
                if (idx >= AVATARS.length) break;

                const container = document.createElement('div');
                container.className = 'avatar-container';
                container.dataset.avatarIndex = idx;

                const img = document.createElement('img');
                img.src = AVATARS[idx];
                img.alt = `Avatar ${idx + 1}`;
                img.loading = 'lazy';
                container.appendChild(img);

                container.addEventListener('click', () => {
                    selectedAvatar = idx;
                    localStorage.setItem('paimon_avatar', idx.toString());
                    highlightAvatar(idx);
                    // Update the avatar in all existing user messages too
                    updateAllUserAvatars(AVATARS[idx]);
                });

                rowEl.appendChild(container);
            }

            avatarGrid.appendChild(rowEl);
        }
    }

    // ============================
    // Greeting
    // ============================
    function showGreeting() {
        const variations = [
            "Just tell Paimon where you want to go, and Paimon will look up the quest requirements! Maybe we'll find some Sticky Honey Roast along the way~",
            "Type the name of any place you wanna explore, and Paimon will check if we need to do any quests first! Oh, Paimon hopes there's treasure...",
            "Let Paimon know where we're heading next! Paimon will make sure we meet all the requirements. Ooh, all this guiding is making Paimon hungry!"
        ];
        
        const randomGreeting = variations[Math.floor(Math.random() * variations.length)];

        const greetings = [
            "Hi Traveler! Paimon's here to help you figure out how to get to new areas!",
            randomGreeting,
        ];

        greetings.forEach((msg, i) => {
            setTimeout(() => {
                appendBotMessage(msg);
            }, i * 600);
        });
    }

    // ============================
    // Paimon Gimmick Replies (greetings, emergency food, etc.)
    // ============================
    function pickRandom(arr) {
        return arr[Math.floor(Math.random() * arr.length)];
    }

    function getPaimonGimmickReply(text) {
        const normalized = text.toLowerCase().replace(/[^\w\s']/g, ' ').replace(/\s+/g, ' ').trim();
        const displayName = nickname || 'Traveler';

        const isGreeting = /^(hi+|hello+|hey+|yo+|hiya+|howdy+|good\s+(morning|afternoon|evening|day|night)|sup|what'?s\s+up)\b/.test(normalized)
            || /^(hi+|hello+|hey+)\s+(paimon|there|traveler|friend)\b/.test(normalized)
            || /\b(hi+|hello+|hey+)\s+paimon\b/.test(normalized);

        const isEmergencyFood = /\bemergency\s+food\b/.test(normalized)
            || /\b(floating|flying)\s+(snack|food)\b/.test(normalized)
            || /\bare\s+you\s+(an?\s+)?(emergency\s+food|snack|food)\b/.test(normalized)
            || /\byou\s+(are|r)\s+(an?\s+)?(emergency\s+food|just\s+a\s+snack)\b/.test(normalized)
            || /\bpaimon\s+(is|are)\s+(an?\s+)?emergency\s+food\b/.test(normalized);

        if (isGreeting) {
            return pickRandom([
                `Ehe~ Hi ${displayName}! Paimon's right here! Got a place you wanna explore? Paimon can look up the quest for you!`,
                `Oh! ${displayName}! Paimon was just thinking about Sticky Honey Roast... anyway, where are we going today?`,
                `Hehe, hello ${displayName}! Paimon's the best guide in Teyvat, you know! So, which area should we check?`,
                `Hi hi! Paimon's ready when you are! Just tell Paimon a location name and Paimon will do the rest~`,
            ]);
        }

        if (isEmergencyFood) {
            return pickRandom([
                `Waaah?! Emergency food?! Paimon is NOT food, ${displayName}! Paimon is your trusted guide! ...and maybe your wallet's worst nightmare at restaurants.`,
                `Hey! Paimon heard that! Paimon is a respectable floating companion, NOT emergency rations! Hmph!`,
                `Ehe~ nice try, ${displayName}! But Paimon refuses to be anyone's snack! Now ask Paimon about a real location instead!`,
                `Floating emergency food?! The nerve! Paimon works hard guiding you around Teyvat! ...unless you mean emergency food for Paimon's stomach?`,
                `Paimon is NOT edible! Paimon is essential! Totally different! ...okay maybe Paimon gets hungry too, but that's not the point!`,
            ]);
        }

        return null;
    }

    function delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ============================
    // Send Message Handler
    // ============================
    async function handleSend() {
        const text = chatInput.value.trim();
        if (!text || isProcessing) return;

        isProcessing = true;
        sendBtn.disabled = true;

        // Show user message
        appendUserMessage(text);
        chatInput.value = '';

        // Show typing indicator
        const typingEl = showTypingIndicator();

        const gimmickReply = getPaimonGimmickReply(text);
        if (gimmickReply) {
            await delay(500 + Math.random() * 400);
            removeTypingIndicator(typingEl);
            appendBotMessage(gimmickReply);
            isProcessing = false;
            sendBtn.disabled = false;
            chatInput.focus();
            return;
        }

        try {
            const response = await fetch('/api/check-quest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify({ area_name: text }),
            });

            // Remove typing indicator
            removeTypingIndicator(typingEl);

            const rawData = await response.json();

            if (response.ok) {
                // Laravel JsonResource wraps in { data: { ... } }
                const data = rawData.data || rawData;

                let reply = '';
                if (data.prerequisite_quest) {
                    // Scenario 1: Quest(s) needed — split newline-separated quests into bullet list
                    const rawQuest = data.prerequisite_quest;
                    const questLines = Array.isArray(rawQuest)
                        ? rawQuest
                        : String(rawQuest).split('\n').map(q => q.trim()).filter(Boolean);

                    if (questLines.length === 0) {
                        reply = `Ooh, no quest needed! We can go explore **${data.area_name}** in ${data.region} right away! Let's go see if there's any treasure!`;
                    } else {
                        const bulletList = questLines.map(q => `<span class="quest-item">• ${q}</span>`).join('');
                        reply = `Hold on, Traveler! Before we can explore **${data.area_name}** in ${data.region}, you need to complete:\n${bulletList}`;
                    }
                } else {
                    // Scenario 2: No quest needed
                    reply = `Ooh, no quest needed! We can go explore **${data.area_name}** in ${data.region} right away! Let's go see if there's any treasure!`;
                }

                appendBotMessage(reply);

            } else if (response.status === 404) {
                // Scenario 3: Area not found in database
                appendBotMessage(
                    `Hmm... Paimon's never heard of "${text}"...\n\nAre you sure you spelled it right, Traveler? Try something like "Enkanomiya", "Dragonspine", or "The Chasm"!`
                );
            } else if (response.status === 422) {
                const errors = rawData.errors || {};
                const errorMsg = Object.values(errors).flat().join('\n');
                appendBotMessage(`Uwah?! ${errorMsg || rawData.message || "Something went wrong and Paimon doesn't know why!"}`);
            } else {
                appendBotMessage(`Waah! Something went wrong... Paimon's head is spinning!`);
            }
        } catch (error) {
            removeTypingIndicator(typingEl);
            appendBotMessage(`Ehe~ Paimon couldn't reach the server! Did you forget to turn it on, Traveler?`, true);
        } finally {
            isProcessing = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    }

    // ============================
    // Chat Message Rendering
    // ============================
    function appendBotMessage(text, isError = false) {
        const card = document.createElement('div');
        card.className = 'message-card message-appear';

        const formattedText = formatText(text);
        const bubbleClass = isError ? 'error-bubble-text' : 'message-bubble-text';
        const tailIcon = isError ? '/images/bubble-tail-error.svg' : '/images/bubble-tail-left.svg';

        card.innerHTML = `
            <img src="/images/profile_selector/Paimon.webp" alt="Paimon" class="message-avatar">
            <div class="message-content">
                <span class="message-sender">Paimon</span>
                <div class="message-bubble">
                    <div class="message-bubble-tail">
                        <img src="${tailIcon}" alt="">
                    </div>
                    <div class="${bubbleClass}">${formattedText}</div>
                </div>
            </div>
        `;

        chatMessages.appendChild(card);
        scrollToBottom();
    }

    function appendUserMessage(text) {
        const card = document.createElement('div');
        card.className = 'response-card message-appear';

        const displayName  = nickname || 'Traveler';
        const avatarSrc    = AVATARS[selectedAvatar] || AVATARS[0];

        card.innerHTML = `
            <div class="response-content">
                <span class="response-sender" data-user-sender="true">${escapeHtml(displayName)}</span>
                <div class="response-bubble">
                    <div class="response-bubble-text">${escapeHtml(text)}</div>
                    <div class="response-bubble-tail">
                        <img src="/images/bubble-tail-right.svg" alt="">
                    </div>
                </div>
            </div>
            <img src="${avatarSrc}" alt="${escapeHtml(displayName)}" class="message-avatar user-avatar-img">
        `;

        chatMessages.appendChild(card);
        scrollToBottom();
    }

    // ============================
    // Retroactive Updates
    // ============================

    /** Update the sender label on every user bubble already in the chat. */
    function updateAllSenderLabels(newName) {
        document.querySelectorAll('[data-user-sender="true"]').forEach(el => {
            el.textContent = newName;
        });
    }

    /** Update the avatar <img> in every user bubble already in the chat. */
    function updateAllUserAvatars(newSrc) {
        document.querySelectorAll('.user-avatar-img').forEach(img => {
            img.src = newSrc;
        });
    }

    // ============================
    // Typing Indicator
    // ============================
    function showTypingIndicator() {
        const card = document.createElement('div');
        card.className = 'message-card message-appear';
        card.id = 'typing-indicator';

        card.innerHTML = `
            <img src="/images/profile_selector/Paimon.webp" alt="Paimon" class="message-avatar">
            <div class="message-content">
                <span class="message-sender">Paimon</span>
                <div class="message-bubble">
                    <div class="message-bubble-tail">
                        <img src="/images/bubble-tail-left.svg" alt="">
                    </div>
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        `;

        chatMessages.appendChild(card);
        scrollToBottom();
        return card;
    }

    function removeTypingIndicator(el) {
        if (el && el.parentNode) {
            el.parentNode.removeChild(el);
        }
    }

    // ============================
    // Avatar Selection
    // ============================
    function highlightAvatar(index) {
        document.querySelectorAll('.avatar-container').forEach((c, i) => {
            c.classList.toggle('selected', i === index);
        });
    }

    // ============================
    // Utilities
    // ============================
    function scrollToBottom() {
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatText(text) {
        // Pull out any pre-built quest-item spans before escaping
        const QUEST_PLACEHOLDER = '\x00QUEST\x00';
        const questSpans = [];
        let safe = text.replace(/<span class="quest-item">([^<]*)<\/span>/g, (_, content) => {
            questSpans.push(content);
            return QUEST_PLACEHOLDER;
        });

        // Now safely escape the rest
        let html = escapeHtml(safe);

        // Restore quest-item spans with their original content
        html = html.replace(new RegExp(escapeHtml(QUEST_PLACEHOLDER), 'g'), () => {
            const q = questSpans.shift();
            return `<span class="quest-item">• ${escapeHtml(q.replace(/^• /, ''))}</span>`;
        });

        // Highlighted text: **text**
        html = html.replace(/\*\*(.*?)\*\*/g, '<span class="highlight-text">$1</span>');
        // Newlines → line breaks
        html = html.replace(/\n/g, '<br>');
        return html;
    }
});

// ============================
// Mobile Drawer Logic
// ============================
(function () {
    const btnLeft     = document.getElementById('btn-open-left');
    const btnRight    = document.getElementById('btn-open-right');
    const sidebarLeft = document.querySelector('.sidebar-left');
    const sidebarRight= document.querySelector('.sidebar-right');
    const backdrop    = document.getElementById('drawer-backdrop');

    if (!btnLeft || !backdrop) return; // desktop — nothing to do

    function openDrawer(side) {
        closeAll();
        if (side === 'left') {
            sidebarLeft.classList.add('drawer-open');
            btnLeft.classList.add('open');
        } else {
            sidebarRight.classList.add('drawer-open');
            btnRight.classList.add('open');
        }
        backdrop.classList.add('active');
        document.body.classList.add('drawer-open');
    }

    function closeAll() {
        sidebarLeft.classList.remove('drawer-open');
        sidebarRight.classList.remove('drawer-open');
        btnLeft.classList.remove('open');
        btnRight.classList.remove('open');
        backdrop.classList.remove('active');
        document.body.classList.remove('drawer-open');
    }

    btnLeft.addEventListener('click', () => {
        sidebarLeft.classList.contains('drawer-open') ? closeAll() : openDrawer('left');
    });

    btnRight.addEventListener('click', () => {
        sidebarRight.classList.contains('drawer-open') ? closeAll() : openDrawer('right');
    });

    backdrop.addEventListener('click', closeAll);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeAll();
    });
})();
