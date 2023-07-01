$(document).ready(function() {
  var currentIndex = 0; // Track the current index of the fetched data

  // Initialize chart
  var ctx = document.getElementById('dataChart').getContext('2d');
  var myChart = new Chart(ctx, {
    type: 'line', // Change type to 'line'
    data: {
      labels: [], // Initialize empty array for city names
      datasets: [{
        label: 'Power Consumption',
        data: [], // Initialize empty array for power averages
        backgroundColor: 'rgba(75, 192, 192, 0.2)', // Change this to preferred color
        borderColor: 'rgba(75, 192, 192, 1)', // Change this to preferred color
        borderWidth: 1,
        fill: false // Ensure the area under the line is not filled
      }]
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
          min: 0,
          max: 700000,
          stepSize: 50000 // Adjust the granularity as needed
        }
      }
    }
  });

  // Function to fetch data from the backend API
  function fetchData() {
    $.ajax({
      url: '/api/data',
      type: 'GET',
      dataType: 'json',
      success: function(data) {
        if (data.length > 0) {
          // Get the city and power average at the current index
          var city = data[currentIndex].cityName;
          var powerAverage = data[currentIndex].powerAverage;

          // Add the city and power average to the chart data
          myChart.data.labels.push(city);
          myChart.data.datasets[0].data.push(powerAverage);

          // If the length of labels/data exceeds 15, remove the first element
          if (myChart.data.labels.length > 15) {
            myChart.data.labels.shift();
            myChart.data.datasets[0].data.shift();
          }

          // Update the chart
          myChart.update();

          // Move to the next index
          currentIndex = (currentIndex + 1) % data.length;
        }
      },
      error: function(error) {
        console.log('Error fetching data:', error);
      }
    });
  }

  // Fetch data initially
  fetchData();

  // Fetch data every 2 seconds
  setInterval(fetchData, 2000);
});
