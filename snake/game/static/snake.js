// snake.js
const canvas = document.getElementById("snakeCanvas");
const ctx = canvas.getContext("2d");

// Game settings
const MOVE_DISTANCE = 10;
const STARTING_POSITIONS = [[0, 0], [10, 0], [20, 0]]; // Example starting positions
const FOOD_SIZE = 8; // Size of the food object
let foodPosition = [100, 100]; // Initial food position

// Snake class
class Snake {
    constructor() {
        this.segments = [];
        this.createSnake();
        this.head = this.segments[0]; // The head is the first segment
        console.log("Snake initialized with head at:", this.head.xcor(), this.head.ycor());
    }

    createSnake() {
        for (const position of STARTING_POSITIONS) {
            this.addSegment(position);
        }
        console.log("Snake created with segments:", this.segments);
    }

    addSegment(position) {
        const newSegment = new Turtle("square");
        newSegment.color("green");
        newSegment.penup();
        // Check if position is an array or a single value
        if (Array.isArray(position)) {
            newSegment.goto(position[0], position[1]);
        } else {
            newSegment.goto(position, position);
        }
        console.log("Added segment at position:", newSegment.xcor(), newSegment.ycor());
        this.segments.push(newSegment);
    }

    extend() {
        this.addSegment(this.segments[this.segments.length - 1].position());
    }

    move() {
        for (let seg_num = this.segments.length - 1; seg_num > 0; seg_num--) {
            const newX = this.segments[seg_num - 1].xcor();
            const newY = this.segments[seg_num - 1].ycor();
            this.segments[seg_num].goto(newX, newY);
        }
        this.head.forward(MOVE_DISTANCE);
        console.log("Snake moved, head position:", this.head.xcor(), this.head.ycor());
    }

    up() {
        this.head.setHeading(90); // Up is 90 degrees
        console.log("Snake direction: up");
    }

    down() {
        this.head.setHeading(270); // Down is 270 degrees
        console.log("Snake direction: down");
    }

    left() {
        this.head.setHeading(180); // Left is 180 degrees
        console.log("Snake direction: left");
    }

    right() {
        this.head.setHeading(0); // Right is 0 degrees
        console.log("Snake direction: right");
    }
}

// Turtle class (simplified for JavaScript)
class Turtle {
    constructor(shape = "square") {
        this.x = 0;
        this.y = 0;
        this.heading = 0; // 0: right, 90: up, 180: left, 270: down
        this.shape = shape; // Not used in this simplified version
        this.color = "green"; // Default color
    }

    penup() {
        // No actual pen up functionality needed in this simplified version
    }

    pendown() {
        // No actual pen down functionality needed in this simplified version
    }

    color(color) {
        this.color = color;
    }

    goto(x, y) {
        // Handle both single parameter (array) and two parameters
        if (y === undefined && Array.isArray(x)) {
            this.x = x[0];
            this.y = x[1];
        } else {
            this.x = x;
            this.y = y;
        }
        console.log("Turtle moved to:", this.x, this.y);
    }

    forward(distance) {
        const angleRad = this.heading * Math.PI / 180;
        this.x += distance * Math.cos(angleRad);
        this.y += distance * Math.sin(angleRad);
    }

    setHeading(heading) {
        this.heading = heading;
    }

    xcor() {
        return this.x;
    }

    ycor() {
        return this.y;
    }

    position(){
        return [this.x, this.y];
    }
}


// Game state variables
let snakePositions = [];
let foodPosition = [100, 100];
let score = 0;
let gameOver = false;

// Fetch initial game state
fetchGameState();

// Event listeners for keyboard input
document.addEventListener("keydown", (event) => {
    let direction = "";
    switch (event.key) {
        case "ArrowUp":
            direction = "up";
            break;
        case "ArrowDown":
            direction = "down";
            break;
        case "ArrowLeft":
            direction = "left";
            break;
        case "ArrowRight":
            direction = "right";
            break;
        default:
            return; // Ignore other keys
    }

    // Send move command to server
    fetch('/move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `direction=${direction}`
    })
    .then(response => response.json())
    .then(data => {
        console.log("Move response:", data);
        // Fetch updated game state
        fetchGameState();
    })
    .catch(error => console.error('Error:', error));
});

// Function to fetch game state from server
function fetchGameState() {
    fetch('/get_state')
        .then(response => response.json())
        .then(data => {
            console.log("Game state:", data);
            snakePositions = data.snake;
            foodPosition = data.food;
            score = data.score;
            gameOver = data.game_over;
        })
        .catch(error => console.error('Error:', error));
}

// Periodically refresh game state (every 500ms)
setInterval(fetchGameState, 500);

// Game loop
function gameLoop() {
    // Clear canvas and set background to black
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw food in yellow
    ctx.fillStyle = "yellow";
    ctx.beginPath();
    ctx.arc(foodPosition[0], foodPosition[1], FOOD_SIZE, 0, Math.PI * 2);
    ctx.fill();

    // Log food position for debugging
    console.log("Food position:", foodPosition);

    // Draw snake segments in green
    ctx.fillStyle = "green";
    for (const segment of snakePositions) {
        // Log segment position for debugging
        console.log("Segment position:", segment[0], segment[1]);
        ctx.fillRect(segment[0] - 5, segment[1] - 5, 10, 10); // Simple rectangle representation
    }

    // Display score
    ctx.fillStyle = "white";
    ctx.font = "20px Arial";
    ctx.fillText(`Score: ${score}`, 10, 30);

    // Check if game is over
    if (gameOver) {
        ctx.fillStyle = "red";
        ctx.font = "40px Arial";
        ctx.fillText("Game Over", canvas.width / 2 - 100, canvas.height / 2);
    }

    // Request next animation frame
    requestAnimationFrame(gameLoop);
}

// Start game loop
gameLoop();
