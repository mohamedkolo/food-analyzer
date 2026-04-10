<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>NutraX</title>
<style>
body { font-family: Arial; margin:0; background:#f5f5f5 }
.container { padding:20px }
.card { background:#fff; padding:20px; margin:10px 0; border-radius:10px }
button { padding:10px 15px; margin:5px; cursor:pointer; border:none; border-radius:5px }
input { padding:10px; margin:5px; width:200px }
.hidden { display:none }
.sidebar { width:200px; background:#222; color:#fff; height:100vh; float:left; padding:20px }
.main { margin-left:220px; padding:20px }
</style>
</head>

<body>

<!-- LOGIN -->
<div id="login" class="container">
  <h2>NutraX Login</h2>
  <input id="email" placeholder="Email"><br>
  <input id="pass" type="password" placeholder="Password"><br>
  <button onclick="login()">Login</button>
</div>

<!-- ADMIN -->
<div id="admin" class="hidden">
  <div class="sidebar">
    <h3>Admin</h3>
    <button onclick="showSection('addFood')">Add Food</button>
    <button onclick="showSection('plans')">Plans</button>
  </div>

  <div class="main">
    <div id="addFood" class="card">
      <h3>Add Food</h3>
      <input id="foodName" placeholder="Food name">
      <input id="cal" placeholder="Calories">
      <button onclick="addFood()">Add</button>
    </div>

    <div id="plans" class="card">
      <h3>Generated Plan</h3>
      <button onclick="generatePlan()">Generate</button>
      <ul id="planList"></ul>
    </div>
  </div>
</div>

<!-- USER -->
<div id="user" class="hidden">
  <div class="container">
    <h2>User Dashboard</h2>

    <select id="goal">
      <option>Fat Loss</option>
      <option>Muscle Gain</option>
      <option>Maintenance</option>
    </select>

    <button onclick="generatePlan()">Get Plan</button>

    <ul id="userPlan"></ul>
  </div>
</div>

<script>

// USERS
const ADMIN_EMAIL = "admin@nutrax.app";
const ADMIN_PASS = "123456";

// DATA
let foods = [
  {name:"Chicken", cal:165},
  {name:"Eggs", cal:155},
  {name:"Rice", cal:200},
  {name:"Fish", cal:180},
  {name:"Oats", cal:150}
];

// LOGIN
function login() {
  let email = document.getElementById("email").value;
  let pass = document.getElementById("pass").value;

  if(email === ADMIN_EMAIL && pass === ADMIN_PASS){
    document.getElementById("login").classList.add("hidden");
    document.getElementById("admin").classList.remove("hidden");
  } else {
    document.getElementById("login").classList.add("hidden");
    document.getElementById("user").classList.remove("hidden");
  }
}

// ADD FOOD
function addFood(){
  let name = document.getElementById("foodName").value;
  let cal = document.getElementById("cal").value;

  foods.push({name, cal});
  alert("Added");
}

// GENERATE PLAN
function generatePlan(){
  let plan = [];
  for(let i=0;i<3;i++){
    let random = foods[Math.floor(Math.random()*foods.length)];
    plan.push(random.name + " ("+random.cal+" cal)");
  }

  let list = document.getElementById("planList") || document.getElementById("userPlan");
  list.innerHTML = "";

  plan.forEach(p=>{
    let li = document.createElement("li");
    li.textContent = p;
    list.appendChild(li);
  });
}

// UI
function showSection(id){
  document.querySelectorAll(".main .card").forEach(el=>el.style.display="none");
  document.getElementById(id).style.display="block";
}

</script>

</body>
</html>
