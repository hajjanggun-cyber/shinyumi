document.addEventListener('DOMContentLoaded', () => {
    fetch('data.json')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#keyword-table tbody');
            tbody.innerHTML = '';

            data.forEach(item => {
                const tr = document.createElement('tr');
                
                // Determine source style
                let sourceClass = 'source-news';
                if (item['출처'] && item['출처'].includes('유튜브')) {
                    sourceClass = 'source-youtube';
                }

                // Create links HTML
                let linksHtml = '';
                if (item['유튜브_URL']) {
                    linksHtml += `<a href="${item['유튜브_URL']}" target="_blank" class="btn-link">YouTube</a>`;
                }
                if (item['뉴스기사_URL']) {
                    linksHtml += `<a href="${item['뉴스기사_URL']}" target="_blank" class="btn-link">News</a>`;
                }
                // Secondary news links (optional, maybe just show primary for cleaner UI or add icons)
                // For now, let's keep it simple with primary links.

                tr.innerHTML = `
                    <td class="rank">${item['순위']}</td>
                    <td class="title">${item['제목']}</td>
                    <td class="score">${item['추천점수']}</td>
                    <td class="keywords">${item['키워드'] || '-'}</td>
                    <td class="source"><span class="${sourceClass}">${item['출처']}</span></td>
                    <td class="links">${linksHtml}</td>
                    <td class="date">${item['업로드일']}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(error => {
            console.error('Error loading data:', error);
            const tbody = document.querySelector('#keyword-table tbody');
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 20px;">데이터를 불러오는 중 오류가 발생했습니다.<br>로컬 서버(serve_web.py)를 실행했는지 확인해주세요.</td></tr>';
        });
});
