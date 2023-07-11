$(document).ready(function () {
  var currentIndex = 0;
  var ctx = document.getElementById('dataChart').getContext('2d');
  var myChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: [],
      datasets: [{
        label: 'Power Consumption',
        data: [],
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1
      }]
    },
    options: {
      scales: {
        x: {
          title: {
            display: true,
            text: 'German Cities'
          },
          ticks: {
            autoSkip: false,
            maxRotation: 90,
            minRotation: 90
          }
        },
        y: {
          title: {
            display: true,
            text: 'Power Consumption (kw/h)'
          },
          beginAtZero: true,
          min: 0,
          max: 400000,
          stepSize: 5000,
        }
      }
    }
  });

  var costDisplay = document.getElementById('costDisplay');

  function fetchData() {
    $.ajax({
      url: '/api/data',
      type: 'GET',
      dataType: 'json',
      success: function (data) {
        if (data.length > 16) {
          costDisplay.innerHTML = '';
          data.forEach(function (item) {
            var city = item.cityName;
            var cost = item.cost.toFixed(2);

            // Only show the city name and cost
            var costItem = document.createElement('div');
            costItem.classList.add('cost-item');
            costItem.innerText = city + ': €' + cost;
            costDisplay.appendChild(costItem);
          });

          var costItems = costDisplay.getElementsByClassName('cost-item');
          var offset = 0;
          Array.from(costItems).forEach(function (item) {
            item.style.transform = 'translateX(' + offset + 'px)';
            offset += 200;
          });

          if (costItems.length > 3) {
            costDisplay.removeChild(costItems[0]);
          }

          currentIndex = (currentIndex + 1) % data.length;
          var city = data[currentIndex].cityName;
          var powerAverage = data[currentIndex].powerAverage;

          myChart.data.labels.push(city);
          myChart.data.datasets[0].data.push(powerAverage);

          if (myChart.data.labels.length > 16) {
            myChart.data.labels.shift();
            myChart.data.datasets[0].data.shift();
          }

          myChart.update();
        }
      },
      error: function (error) {
        console.log('Error fetching data:', error);
      }
    });
  }

  fetchData();
  setInterval(fetchData, 10000);

  $("#schemaImage").click(function () {
    $("#enlargedSchemaImage").addClass("show");
  });

  $("#enlargedSchemaImage").click(function () {
    $(this).removeClass("show");
  });
});
