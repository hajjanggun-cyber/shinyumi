document.addEventListener('DOMContentLoaded', () => {
    // State for selection
    let currentTopic = '정치';
    let currentPeriod = 'today';

    // UI Elements
    const topicBtns = document.querySelectorAll('#topic-group .select-btn');
    const periodBtns = document.querySelectorAll('#period-group .select-btn');
    const searchBtn = document.getElementById('search-btn');
    const overlay = document.getElementById('landing-overlay');
    const content = document.getElementById('content');
    const tbody = document.querySelector('#keyword-table tbody');

    // Handle Topic Selection
    topicBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            topicBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTopic = btn.dataset.value;
        });
    });

    // Handle Period Selection
    periodBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            periodBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPeriod = btn.dataset.value;
        });
    });

    // Handle Search Click
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            // Filter Data
            const filteredData = filterData(currentTopic, currentPeriod);
            renderTable(filteredData);

            // Show Content
            overlay.style.opacity = '0';
            setTimeout(() => {
                overlay.style.display = 'none';
                content.style.display = 'block';
                backBtn.style.display = 'block'; // Show back button
            }, 300);
        });
    }

    // Create 'Back to Search' button dynamically
    const backBtn = document.createElement('button');
    backBtn.id = 'back-btn';
    backBtn.textContent = '처음으로';
    backBtn.style.cssText = 'display: none; margin: 0 auto 20px; padding: 10px 20px; font-size: 16px; background: #666; color: white; border: none; border-radius: 5px; cursor: pointer;';
    backBtn.addEventListener('click', () => {
        // Reset UI
        content.style.display = 'none';
        backBtn.style.display = 'none';
        overlay.style.display = 'flex';
        setTimeout(() => {
            overlay.style.opacity = '1';
        }, 10);
    });

    // Insert back button before table
    const tableContainer = document.querySelector('.table-container');
    if (tableContainer) {
        content.insertBefore(backBtn, tableContainer);
    } else {
        content.insertBefore(backBtn, content.firstChild);
    }

    // Helper: Parse date string "YYYY-MM-DD" or "2024-02-01 ..."
    function parseDate(dateStr) {
        if (!dateStr) return null;
        // Extract YYYY-MM-DD
        const match = dateStr.match(/(\d{4}-\d{2}-\d{2})/);
        return match ? new Date(match[1]) : null;
    }

    // Filter Logic
    function filterData(topic, period) {
        if (typeof keywordData === 'undefined') return [];

        const now = new Date();
        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()); // 00:00 today

        return keywordData.filter(item => {
            // 1. Topic Filter
            // item['카테고리'] might be undefined for old data, but new run_all.py adds it.
            // If undefined, assume '정치' for backward compatibility or just exclude.
            const itemCategory = item['카테고리'] || '정치';
            if (itemCategory !== topic) return false;

            // 2. Period Filter
            const itemDate = parseDate(item['업로드일']);
            if (!itemDate) return true; // If no date, include it (or exclude?) -> Let's include

            const diffTime = now - itemDate;
            const diffDays = diffTime / (1000 * 60 * 60 * 24);

            if (period === 'today') {
                return itemDate >= todayStart;
            } else if (period === '3days') {
                return diffDays <= 3;
            } else if (period === '1week') {
                return diffDays <= 7;
            } else if (period === '1month') {
                return diffDays <= 30;
            }
            return true;
        });
    }

    function renderTable(data) {
        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 20px;">해당 조건의 데이터가 없습니다.</td></tr>';
            return;
        }

        data.forEach((item, index) => { // Re-index for display? Or keep original rank? Let's use loop index for current view rank
            const tr = document.createElement('tr');

            // Determine source style
            let sourceClass = 'source-news';
            let sourceText = item['출처'];
            if (sourceText && sourceText.includes('유튜브')) {
                sourceClass = 'source-youtube';
            }

            // Create links HTML (Multi-line)
            const urls = [];
            // 순서대로 추가 (유튜브/뉴스1 -> 뉴스2 -> 뉴스3)
            if (item['유튜브_URL']) urls.push(item['유튜브_URL']);
            if (item['뉴스기사_URL']) urls.push(item['뉴스기사_URL']);
            if (item['뉴스기사2_URL']) urls.push(item['뉴스기사2_URL']);
            if (item['뉴스기사3_URL']) urls.push(item['뉴스기사3_URL']);

            // 중복 제거 및 공백 제거
            const uniqueUrls = [...new Set(urls.filter(u => u))];

            let linksHtml = '';
            if (uniqueUrls.length > 0) {
                linksHtml = uniqueUrls.map(url => `<a href="${url}" target="_blank">${url}</a>`).join('<br>');
            }

            tr.innerHTML = `
                <td class="rank">${index + 1}</td>
                <td class="title" title="${item['제목']}">${item['제목']}</td>
                <td class="score">${item['추천점수']}</td>
                <td class="keywords" title="${item['키워드'] || ''}">${item['키워드'] || ''}</td>
                <td class="source"><span class="${sourceClass}">${sourceText}</span></td>
                <td class="links">${linksHtml}</td>
                <td class="date">${item['업로드일']}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Initial check (don't render automatically, wait for user input)
    if (typeof keywordData === 'undefined') {
        // Just show alert or log if needed, but overlay covers it.
        console.error("Data file not loaded.");
    } else {
        // Check for scraper errors
        if (typeof scraperStatus !== 'undefined') {
            const errors = [];
            for (const [source, status] of Object.entries(scraperStatus)) {
                if (status !== 'OK') {
                    // 소스 이름 한글로 변환
                    let sourceName = source;
                    if (source === 'youtube') sourceName = '유튜브';
                    else if (source === 'google') sourceName = '구글뉴스';
                    else if (source === 'naver') sourceName = '네이버뉴스';

                    errors.push(`[${sourceName}] ${status}`);
                }
            }

            if (errors.length > 0) {
                const alertDiv = document.createElement('div');
                alertDiv.style.cssText = 'background: #ffebee; color: #c62828; padding: 15px; margin: 20px 0; border-radius: 8px; border: 1px solid #ef9a9a; font-weight: bold; line-height: 1.6;';
                alertDiv.innerHTML = `⚠️ 데이터 수집 중 일부 오류가 발생했습니다 (건너뜀):<br>${errors.join('<br>')}`;

                // content 내부 최상단에 추가
                content.insertBefore(alertDiv, content.firstChild);
            }
        }
    }
});
