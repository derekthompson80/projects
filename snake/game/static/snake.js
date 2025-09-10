// snake.js - Snake game implementation for Flask
const canvas = document.getElementById("snakeCanvas");
const ctx = canvas.getContext("2d");
const currentScoreElement = document.getElementById("current-score");
const highScoreElement = document.getElementById("high-score");
const gameOverContainer = document.getElementById("game-over-container");
const finalScoreElement = document.getElementById("final-score");
const newHighScoreElement = document.getElementById("new-high-score");
const resetButton = document.getElementById("reset-button");
const restartButton = document.getElementById("restart-button");

// Game settings
const GRID_SIZE = 600;
const CELL_SIZE = 20;
const MOVE_DISTANCE = 20;
const GAME_SPEED = 50; // milliseconds for rendering
const MOVE_INTERVAL = 200; // milliseconds between snake movements

// Game state variables
let snakePositions = [];
let foodPosition = [100, 100];
let score = 0;
let highScore = parseInt(highScoreElement.textContent.split(": ")[1]) || 0;
let gameOver = false;
let gameStarted = false; // Track whether the game has started
let lastDirection = "right"; // Default direction
let gameLoopInterval;
let lastMoveTime = 0; // Track the last time the snake moved
let currentMoveInterval = MOVE_INTERVAL; // Current movement interval that will change with score

// Colors
const COLORS = ["white", "red", "orange", "yellow", "green", "blue", "purple", "pink", "cyan", "magenta"];
let snakeColor = "green";
let foodColor = "red";
let backgroundColor = "black";

// Initialize the game
initGame();

// Event listeners for keyboard input
document.addEventListener("keydown", handleKeyPress);
const startButton = document.getElementById("start-button");
startButton.addEventListener("click", startGame);
resetButton.addEventListener("click", resetGame);
restartButton.addEventListener("click", resetGame);

// Function to initialize the game
function initGame() {
    // Initialize lastMoveTime
    lastMoveTime = Date.now();

    // Initialize movement interval
    currentMoveInterval = MOVE_INTERVAL;

    // Fetch initial game state
    fetchGameState();

    // Start game loop
    startGameLoop();
}

// Function to start the game
function startGame() {
    if (!gameOver) {
        gameStarted = true;
        startButton.disabled = true;
        startButton.textContent = "Game Started";
    }
}

// Function to handle key presses
function handleKeyPress(event) {
    if (gameOver || !gameStarted) return;

    // Only update the direction; do not move immediately.
    switch (event.key) {
        case "ArrowUp":
            if (lastDirection !== "down") {
                lastDirection = "up";
            }
            break;
        case "ArrowDown":
            if (lastDirection !== "up") {
                lastDirection = "down";
            }
            break;
        case "ArrowLeft":
            if (lastDirection !== "right") {
                lastDirection = "left";
            }
            break;
        case "ArrowRight":
            if (lastDirection !== "left") {
                lastDirection = "right";
            }
            break;
        default:
            return; // Ignore other keys
    }

    // Movement will occur on the next tick in gameLoop() based on lastDirection.
}

// Function to move the snake
function moveSnake(direction) {
    fetch('/move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `direction=${direction}`
    })
    .then(response => response.json())
    .then(data => {
        // Update score
        if (data.score !== undefined) {
            score = data.score;
            currentScoreElement.textContent = `Score: ${score}`;
            // Update snake speed based on new score
            updateSnakeSpeed();
            // Update snake color based on score
            updateSnakeColor();
        }

        // Update high score
        if (data.high_score !== undefined && data.high_score > highScore) {
            highScore = data.high_score;
            highScoreElement.textContent = `High Score: ${highScore}`;
        }

        // Check for game over
        if (data.message === "game over") {
            handleGameOver(data);
        } else {
            // Only fetch updated game state if not game over
            fetchGameState();
        }
    })
    .catch(error => console.error('Error:', error));
}

// Function to fetch game state from server
function fetchGameState() {
    fetch('/get_state')
        .then(response => response.json())
        .then(data => {
            snakePositions = data.snake;
            foodPosition = data.food;
            score = data.score;
            gameOver = data.game_over;

            // Update score display
            currentScoreElement.textContent = `Score: ${score}`;

            // Ensure speed reflects the current score even on state fetch
            updateSnakeSpeed();

            // Update high score display if needed
            if (data.high_score > highScore) {
                highScore = data.high_score;
                highScoreElement.textContent = `High Score: ${highScore}`;
            }

            // Check for game over
            if (gameOver) {
                handleGameOver(data);
            }
        })
        .catch(error => console.error('Error:', error));
}

// Function to handle game over
function handleGameOver(data) {
    gameOver = true;
    clearInterval(gameLoopInterval);

    // Update final score
    finalScoreElement.textContent = `Your score: ${score}`;

    // Check if it's a new high score
    if (score >= highScore) {
        newHighScoreElement.style.display = "block";
    } else {
        newHighScoreElement.style.display = "none";
    }

    // Show game over message
    gameOverContainer.style.display = "block";
}

// Function to reset the game
function resetGame() {
    // Hide game over message
    gameOverContainer.style.display = "none";

    // Reset game state on server
    fetch('/reset_game', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        // Reset local game state
        gameOver = false;
        gameStarted = false;
        score = 0;
        lastDirection = "right";
        lastMoveTime = Date.now();
        // Reset snake speed
        currentMoveInterval = MOVE_INTERVAL;
        // Reset snake color
        snakeColor = "green";

        // Reset start button
        startButton.disabled = false;
        startButton.textContent = "Start Game";

        // Update score display
        currentScoreElement.textContent = `Score: ${score}`;

        // Fetch updated game state
        fetchGameState();

        // Restart game loop
        startGameLoop();
    })
    .catch(error => console.error('Error:', error));
}

// Function to start the game loop
function startGameLoop() {
    // Clear any existing interval
    if (gameLoopInterval) {
        clearInterval(gameLoopInterval);
    }

    // Start new game loop
    gameLoopInterval = setInterval(gameLoop, GAME_SPEED);
}

// Game loop
function gameLoop() {
    // Get current time
    const currentTime = Date.now();

    // Clear canvas and set background
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid (optional)
    drawGrid();

    // Draw food
    drawFood();

    // Draw snake
    drawSnake();

    // Automatically move the snake in the current direction at specified intervals
    if (!gameOver && gameStarted && (currentTime - lastMoveTime >= currentMoveInterval)) {
        moveSnake(lastDirection);
        lastMoveTime = currentTime;
    } else if (gameOver) {
        // If game is over, stop the loop
        clearInterval(gameLoopInterval);
    }
}

// Function to draw the grid
function drawGrid() {
    ctx.strokeStyle = "#333333";
    ctx.lineWidth = 0.5;

    // Draw vertical lines
    for (let x = 0; x <= GRID_SIZE; x += CELL_SIZE) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, GRID_SIZE);
        ctx.stroke();
    }

    // Draw horizontal lines
    for (let y = 0; y <= GRID_SIZE; y += CELL_SIZE) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(GRID_SIZE, y);
        ctx.stroke();
    }
}

// Function to draw the food
function drawFood() {
    ctx.fillStyle = foodColor;

    // Convert from game coordinates to canvas coordinates
    const x = foodPosition[0] + GRID_SIZE / 2;
    const y = GRID_SIZE / 2 - foodPosition[1];

    // Draw a circle for the food
    ctx.beginPath();
    ctx.arc(x, y, CELL_SIZE / 2, 0, Math.PI * 2);
    ctx.fill();
}

// Function to draw the snake
function drawSnake() {
    // Draw each segment of the snake
    for (let i = 0; i < snakePositions.length; i++) {
        // Use different color for head
        if (i === 0) {
            ctx.fillStyle = "lightgreen";
        } else {
            ctx.fillStyle = snakeColor;
        }

        // Convert from game coordinates to canvas coordinates
        const x = snakePositions[i][0] + GRID_SIZE / 2;
        const y = GRID_SIZE / 2 - snakePositions[i][1];

        // Draw a rounded rectangle for each segment
        roundedRect(ctx, x - CELL_SIZE / 2, y - CELL_SIZE / 2, CELL_SIZE, CELL_SIZE, 4);
    }
}

// Helper function to draw rounded rectangles
function roundedRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + width, y, x + width, y + height, radius);
    ctx.arcTo(x + width, y + height, x, y + height, radius);
    ctx.arcTo(x, y + height, x, y, radius);
    ctx.arcTo(x, y, x + width, y, radius);
    ctx.closePath();
    ctx.fill();
}

// Change snake color based on score (optional feature)
function updateSnakeColor() {
    // Change color every 5 points
    if (score > 0 && score % 5 === 0) {
        const colorIndex = (score / 5) % COLORS.length;
        snakeColor = COLORS[colorIndex];
    }
}

// Update snake speed based on score
function updateSnakeSpeed() {
    // Double the speed (halve the interval) every 5 points.
    // Keep a minimum interval of 50ms to remain playable.
    const MIN_INTERVAL = 50;

    if (score > 0) {
        const tiers = Math.floor(score / 5); // 0 at <5, 1 at 5–9, 2 at 10–14, etc.
        const newInterval = Math.max(MIN_INTERVAL, Math.floor(MOVE_INTERVAL / Math.pow(2, tiers)));

        // If interval changed, apply it and rebaseline lastMoveTime so change takes effect immediately.
        if (newInterval !== currentMoveInterval) {
            currentMoveInterval = newInterval;
            lastMoveTime = Date.now();
        }
        console.log(`Score: ${score}, Tiers: ${tiers}, Current interval: ${currentMoveInterval}ms`);
    } else {
        // Reset to default speed
        currentMoveInterval = MOVE_INTERVAL;
        lastMoveTime = Date.now();
    }
}
