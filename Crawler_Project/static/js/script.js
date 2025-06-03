function loadCategory(category) {
    const encodedCategory = encodeURIComponent(category);
    fetch(`/get_top_words/${encodedCategory}`)
        .then(response => response.json())
        .then(data => {
            console.log("Received data:", data);  // 디버그 출력 추가
            renderWordCloud(data);
            renderWordList(data);
        });
}

function renderWordCloud(data) {
    d3.select("#wordcloud").selectAll("*").remove();

    const width = 600;  // 크기를 조정합니다.
    const height = 400;  // 크기를 조정합니다.

    const layout = d3.layout.cloud()
        .size([width, height])
        .words(data.map(d => ({ text: d[0], size: d[1] * 2 })))  // 크기를 작게 조정하여 단어가 더 많이 보이도록
        .padding(5)
        .rotate(() => ~~(Math.random() * 2) * 90)
        .font("Impact")
        .fontSize(d => d.size)
        .on("end", draw);

    layout.start();

    function draw(words) {
        const color = d3.scaleOrdinal(d3.schemeCategory10);

        d3.select("#wordcloud")
            .append("svg")
            .attr("width", layout.size()[0])
            .attr("height", layout.size()[1])
            .append("g")
            .attr("transform", "translate(" + layout.size()[0] / 2 + "," + layout.size()[1] / 2 + ")")
            .selectAll("text")
            .data(words)
            .enter().append("text")
            .style("font-size", d => d.size + "px")
            .style("font-family", "Impact")
            .style("fill", (d, i) => d3.interpolateRainbow(i / words.length))
            .attr("text-anchor", "middle")
            .attr("transform", d => "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")")
            .text(d => d.text);
    }
}

function renderWordList(data) {
    const wordList = document.getElementById("wordlist");
    wordList.innerHTML = "";
    data.forEach(d => {
        const li = document.createElement("li");
        li.textContent = d[0];
        wordList.appendChild(li);
    });
}

function searchWord() {
    const word = document.getElementById("search-word").value;
    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ word })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Search results:", data);
        renderSearchResults(data);
    });
}

function renderSearchResults(data) {
    const linksContainer = document.getElementById("links");
    linksContainer.innerHTML = "";
    data.forEach(item => {
        const linkItem = document.createElement("div");
        const linkTitle = document.createElement("a");
        linkTitle.href = item.link;
        linkTitle.textContent = item.title;
        linkTitle.target = "_blank";
        linkItem.appendChild(linkTitle);
        linksContainer.appendChild(linkItem);
    });
}

document.addEventListener("DOMContentLoaded", function() {
    const buttons = document.querySelectorAll(".category-button");
    const wordList = document.getElementById("wordlist");
    const wordCloudContainer = document.getElementById("wordcloud");
    const linksContainer = document.getElementById("links");
    const searchForm = document.getElementById("search-form");

    buttons.forEach(button => {
        button.addEventListener("click", function() {
            const category = encodeURIComponent(button.innerText);
            fetch(`/get_top_words/${category}`)
                .then(response => response.json())
                .then(data => {
                    wordList.innerHTML = "";
                    linksContainer.innerHTML = "";
                    data.forEach(word => {
                        const li = document.createElement("li");
                        li.textContent = word;
                        wordList.appendChild(li);
                    });
                    renderWordCloud(data);
                });
        });
    });

    searchForm.addEventListener("submit", function(event) {
        event.preventDefault();
        const word = document.getElementById("search-word").value;
        fetch("/search", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ word: word })
        })
            .then(response => response.json())
            .then(links => {
                linksContainer.innerHTML = "";
                const linkList = document.createElement("ul");
                links.forEach(link => {
                    const linkLi = document.createElement("li");
                    const a = document.createElement("a");
                    a.href = link.link;
                    a.textContent = link.title;
                    a.target = "_blank";
                    linkLi.appendChild(a);
                    linkList.appendChild(linkLi);
                });
                linksContainer.appendChild(linkList);
            });
    });
});