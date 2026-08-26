// ==UserScript==
// @name         MJJBox TL3 Requirements Button
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Add TL3 requirements button to user level panel on mjjbox.com
// @author       Your Name
// @match        https://mjjbox.com/*
// @grant        GM_addStyle
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    GM_addStyle(`
        .mjjbox-panel-controls {
            display: flex;
            gap: 10px;
            margin-top: 12px;
            flex-wrap: wrap;
        }

        .mjjbox-btn-tl3 {
            display: inline-flex;
            align-items: center;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.3s ease;
            cursor: pointer;
            border: 2px solid;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-color: #667eea;
            color: #ffffff;
            box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
        }

        .mjjbox-btn-tl3:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }

        .mjjbox-btn-tl3:active {
            transform: translateY(0);
            box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
        }

        .mjjbox-btn-tl3.disabled {
            opacity: 0.5;
            cursor: not-allowed;
            pointer-events: none;
            background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
            border-color: #9ca3af;
        }

        .mjjbox-btn-tl3-tooltip {
            position: relative;
            display: inline-block;
        }

        .mjjbox-btn-tl3-tooltip .tooltiptext {
            visibility: hidden;
            width: 200px;
            background-color: #555;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 8px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 12px;
        }

        .mjjbox-btn-tl3-tooltip .tooltiptext::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #555 transparent transparent transparent;
        }

        .mjjbox-btn-tl3-tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }

        @media (prefers-color-scheme: dark) {
            .mjjbox-btn-tl3 {
                background: linear-gradient(135deg, #4c51bf 0%, #553c9a 100%);
                border-color: #4c51bf;
            }

            .mjjbox-btn-tl3:hover {
                background: linear-gradient(135deg, #553c9a 0%, #4c51bf 100%);
                box-shadow: 0 4px 8px rgba(76, 81, 191, 0.4);
            }
        }

        body.theme-light .mjjbox-btn-tl3 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-color: #667eea;
        }

        body.theme-dark .mjjbox-btn-tl3 {
            background: linear-gradient(135deg, #4c51bf 0%, #553c9a 100%);
            border-color: #4c51bf;
        }

        body.theme-tech .mjjbox-btn-tl3 {
            background: linear-gradient(135deg, #00ff87 0%, #00d4ff 100%);
            border-color: #00ff87;
            color: #000000;
        }

        body.theme-tech .mjjbox-btn-tl3:hover {
            background: linear-gradient(135deg, #00d4ff 0%, #00ff87 100%);
            box-shadow: 0 4px 8px rgba(0, 255, 135, 0.4);
        }
    `);

    let currentUserData = null;
    let isAdmin = false;

    async function fetchUserData() {
        try {
            const response = await fetch('/api/user/current', {
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                console.warn('Failed to fetch user data:', response.status);
                return null;
            }

            const data = await response.json();
            
            if (data && data.user) {
                isAdmin = data.user.admin === true || 
                          data.user.role === 'admin' || 
                          (data.user.permissions && data.user.permissions.includes('admin'));
                
                return {
                    userId: data.user.id,
                    username: data.user.username || data.user.name,
                    isAdmin: isAdmin
                };
            }
            
            return null;
        } catch (error) {
            console.error('Error fetching user data:', error);
            return null;
        }
    }

    function extractUserDataFromPage() {
        const userIdMatch = window.location.pathname.match(/\/users\/(\d+)/);
        const userId = userIdMatch ? userIdMatch[1] : null;
        
        const usernameElement = document.querySelector('.user-name, .username, [data-username]');
        const username = usernameElement ? 
            (usernameElement.textContent || usernameElement.dataset.username) : null;
        
        if (userId && username) {
            return { userId, username: username.trim() };
        }
        
        return null;
    }

    async function checkAdminPermission() {
        try {
            const testResponse = await fetch('/admin/users', {
                method: 'HEAD',
                credentials: 'include'
            });
            
            return testResponse.ok || testResponse.status !== 403;
        } catch (error) {
            return false;
        }
    }

    function createTL3Button(userData) {
        const wrapper = document.createElement('div');
        wrapper.className = 'mjjbox-btn-tl3-tooltip';
        
        const button = document.createElement('a');
        button.className = 'mjjbox-btn-tl3';
        button.textContent = '📊 查看详细要求';
        
        if (!userData || !userData.userId || !userData.username) {
            button.classList.add('disabled');
            button.href = 'javascript:void(0)';
            
            const tooltip = document.createElement('span');
            tooltip.className = 'tooltiptext';
            tooltip.textContent = '无法获取用户信息';
            wrapper.appendChild(tooltip);
        } else if (!isAdmin) {
            button.classList.add('disabled');
            button.href = 'javascript:void(0)';
            
            const tooltip = document.createElement('span');
            tooltip.className = 'tooltiptext';
            tooltip.textContent = '需要管理员权限才能查看';
            wrapper.appendChild(tooltip);
        } else {
            button.href = `https://mjjbox.com/admin/users/${userData.userId}/${userData.username}/tl3_requirements`;
            button.target = '_blank';
            button.rel = 'noopener noreferrer';
        }
        
        wrapper.appendChild(button);
        return wrapper;
    }

    function findOrCreateControlsContainer(levelPanel) {
        let controls = levelPanel.querySelector('.mjjbox-panel-controls');
        
        if (!controls) {
            controls = document.createElement('div');
            controls.className = 'mjjbox-panel-controls';
            levelPanel.appendChild(controls);
        }
        
        return controls;
    }

    async function updateLevelPanel(levelPanel) {
        if (levelPanel.querySelector('.mjjbox-btn-tl3')) {
            return;
        }
        
        if (!currentUserData) {
            currentUserData = await fetchUserData();
            
            if (!currentUserData) {
                currentUserData = extractUserDataFromPage();
            }
            
            if (currentUserData && !isAdmin) {
                isAdmin = await checkAdminPermission();
                currentUserData.isAdmin = isAdmin;
            }
        }
        
        const controls = findOrCreateControlsContainer(levelPanel);
        const tl3Button = createTL3Button(currentUserData);
        controls.appendChild(tl3Button);
    }

    async function createLevelPanel() {
        const existingPanel = document.querySelector('.mjjbox-level-panel');
        if (existingPanel) {
            await updateLevelPanel(existingPanel);
            return existingPanel;
        }
        
        const panel = document.createElement('div');
        panel.className = 'mjjbox-level-panel';
        
        const title = document.createElement('h3');
        title.textContent = '用户等级信息';
        panel.appendChild(title);
        
        await updateLevelPanel(panel);
        
        const mainContent = document.querySelector('.main-content, #content, .content');
        if (mainContent) {
            mainContent.insertBefore(panel, mainContent.firstChild);
        } else {
            document.body.appendChild(panel);
        }
        
        return panel;
    }

    function observePageChanges() {
        const observer = new MutationObserver(async (mutations) => {
            for (const mutation of mutations) {
                if (mutation.addedNodes.length > 0) {
                    const levelPanel = document.querySelector('.mjjbox-level-panel, .level-panel, .user-level-panel');
                    if (levelPanel && !levelPanel.querySelector('.mjjbox-btn-tl3')) {
                        await updateLevelPanel(levelPanel);
                    }
                }
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    async function init() {
        await new Promise(resolve => {
            if (document.readyState === 'complete' || document.readyState === 'interactive') {
                resolve();
            } else {
                window.addEventListener('DOMContentLoaded', resolve);
            }
        });
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const levelPanel = document.querySelector('.mjjbox-level-panel, .level-panel, .user-level-panel');
        
        if (levelPanel) {
            await updateLevelPanel(levelPanel);
        } else {
            await createLevelPanel();
        }
        
        observePageChanges();
    }

    init();
})();
