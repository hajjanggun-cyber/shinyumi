document.addEventListener('DOMContentLoaded', () => {
    // Landing Page Logic
    const enterBtn = document.getElementById('enter-btn');
    const overlay = document.getElementById('landing-overlay');
    const content = document.getElementById('content');

    if (enterBtn) {
        enterBtn.addEventListener('click', () => {
            overlay.style.opacity = '0';
            setTimeout(() => {
                overlay.style.display = 'none';
                content.style.display = 'block';
            }, 300); // Wait for transition
        });
    }

    // Check if keywordData is defined (loaded from data.js)
    if (typeof keywordData === 'undefined') {
        document.querySelector('#keyword-table tbody').innerHTML =
            '<tr><td colspan="7" style="text-align:center; padding: 20px;">데이터를 불러올 수 없습니다.<br>run_all.py를 실행하여 data.js 파일을 생성해주세요.</td></tr>';
        return;
    }

    const tbody = document.querySelector('#keyword-table tbody');
    tbody.innerHTML = '';

    keywordData.forEach(item => {
        const tr = document.createElement('tr');

        // Determine source style
        let sourceClass = 'source-news';
        let sourceText = item['출처'];
        if (sourceText && sourceText.includes('유튜브')) {
            sourceClass = 'source-youtube';
        }

        // Create links HTML (Excel style: full URL or "Link")
        // The screenshot shows full URLs mostly. Let's show full URL but truncated if too long in CSS
        let linkUrl = item['유튜브_URL'] || item['뉴스기사_URL'] || '';
        let linksHtml = '';
        if (linkUrl) {
            linksHtml = `<a href="${linkUrl}" target="_blank">${linkUrl}</a>`;
        } else {
            // Try secondary links if primary is empty (though unlikely for valid rows)
            if (item['뉴스기사2_URL']) linksHtml = `<a href="${item['뉴스기사2_URL']}" target="_blank">${item['뉴스기사2_URL']}</a>`;
        }

        tr.innerHTML = `
            <td class="rank">${item['순위']}</td>
            <td class="title" title="${item['제목']}">${item['제목']}</td>
            <td class="score">${item['추천점수']}</td>
            <td class="keywords" title="${item['키워드'] || ''}">${item['키워드'] || ''}</td>
            <td class="source"><span class="${sourceClass}">${sourceText}</span></td>
            <td class="links">${linksHtml}</td>
            <td class="date">${item['업로드일']}</td>
        `;
        tbody.appendChild(tr);
    });
});
