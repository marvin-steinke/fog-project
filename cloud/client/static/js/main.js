$(document).ready(function () {
  var currentIndex = 0; // Track the current index of the fetched data

  // Initialize chart
  var ctx = document.getElementById('dataChart').getContext('2d');
  var myChart = new Chart(ctx, {
    type: 'bar', // Change type to 'bar' to display the shape of data points
    data: {
      labels: [], // Initialize empty array for city names
      datasets: [{
        label: 'Power Consumption',
        data: [], // Initialize empty array for power averages
        backgroundColor: 'rgba(75, 192, 192, 0.2)', // Change this to preferred color
        borderColor: 'rgba(75, 192, 192, 1)', // Change this to preferred color
        borderWidth: 1
      }]
    },
    options: {
      scales: {
        x: { // Display all the German cities on the x-axis
          title: {
            display: true,
            text: 'German Cities'
          },
          ticks: {
            autoSkip: false, // Prevent skipping of x-axis labels
            maxRotation: 90, // Rotate x-axis labels if needed
            minRotation: 90
          }
        },
        y: {
          beginAtZero: true,
          min: 0,
          max: 700000,
          stepSize: 50000 // Adjust the granularity as needed
        }
      }
    }
  });

  // Display the cost per city
  var costDisplay = document.getElementById('costDisplay');

  // Function to fetch data from the backend API
  function fetchData() {
    $.ajax({
      url: '/api/data',
      type: 'GET',
      dataType: 'json',
      success: function (data) {
        if (data.length > 16) {
          // Clear the previous content
          costDisplay.innerHTML = '';

          // Iterate over the data and update the costDisplay
          data.forEach(function (item) {
            var city = item.cityName;
            var cost = item.cost.toFixed(2);
            var costItem = document.createElement('div');
            costItem.classList.add('cost-item');
            costItem.innerText = 'Cost of ' + city + ': €' + cost;
            costDisplay.appendChild(costItem);
          });

          // Slide the cost elements from left to right
          var costItems = costDisplay.getElementsByClassName('cost-item');
          var offset = 0;
          Array.from(costItems).forEach(function (item) {
            item.style.transform = 'translateX(' + offset + 'px)';
            offset += 200; // Adjust the slide distance as needed
          });

          // Remove the oldest cost element if there are more than 5
          if (costItems.length > 5) {
            costDisplay.removeChild(costItems[0]);
          }

          // Move to the next index
          currentIndex = (currentIndex + 1) % data.length;

          // Get the city, power average, and cost at the current index
          var city = data[currentIndex].cityName;
          var powerAverage = data[currentIndex].powerAverage;
          var cost = data[currentIndex].cost;

          // Add the city and power average to the chart data
          myChart.data.labels.push(city);
          myChart.data.datasets[0].data.push(powerAverage);

          // If the length of labels/data exceeds 5, remove the first element
          if (myChart.data.labels.length > 16) {
            myChart.data.labels.shift();
            myChart.data.datasets[0].data.shift();
          }

          // Update the chart
          myChart.update();
        }
      },
      error: function (error) {
        console.log('Error fetching data:', error);
      }
    });
  }

  // Fetch data initially
  fetchData();

  // Fetch data every 2 seconds
  setInterval(fetchData, 5000);

  // Click event for the schema image
  $("#schemaImage").click(function () {
    $("#enlargedSchemaImage").addClass("show");
  });

  // Click event to close the enlarged image
  $("#enlargedSchemaImage").click(function () {
    $(this).removeClass("show");
  });
});
