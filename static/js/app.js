document.getElementById("predictBtn").addEventListener("click", async () => {

    const data = {
        location: document.getElementById("location").value,
        cuisines: document.getElementById("cuisines").value,
        cost: document.getElementById("cost").value,
        rest_type: document.getElementById("rest_type").value,
        votes: document.getElementById("votes").value,
        online_order: document.getElementById("online-order").checked ? 1 : 0,
        book_table: document.getElementById("table-booking").checked ? 1 : 0
    };

    let res = await fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });

    let result = await res.json();

    document.getElementById("output1").innerHTML = result.rating;
    document.getElementById("output2").innerHTML = result.remark;
});
