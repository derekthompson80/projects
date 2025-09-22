def print_board(board):
    print(f" {board[0]} | {board[1]} | {board[2]}")
    print("-----------")
    print(f" {board[3]} | {board[4]} | {board[5]}")
    print("-----------")
    print(f" {board[6]} | {board[7]} | {board[8]}")


def check_win(board, player):
    # Check rows
    for i in range(0, 9, 3):
        if board[i] == board[i + 1] == board[i + 2] == player:
            return True
    # Check columns
    for i in range(3):
        if board[i] == board[i + 3] == board[i + 6] == player:
            return True
    # Check diagonals
    if board[0] == board[4] == board[8] == player:
        return True
    if board[2] == board[4] == board[6] == player:
        return True
    return False


def main():
    board = [' '] * 9
    current_player = 'X'

    print("Welcome to Tic Tac Toe!")
    print("Player 1: X")
    print("Player 2: O")
    print("Enter numbers 1-9 to place your mark on the board")

    while True:
        print_board(board)

        try:
            move = int(input(f"\nPlayer {current_player}, enter your move (1-9): "))

            if move < 1 or move > 9:
                print("Invalid move. Please enter a number between 1 and 9.")
                continue

            index = move - 1
            if board[index] != ' ':
                print("That position is already taken. Please choose another.")
                continue

            board[index] = current_player

            # Check for win
            if check_win(board, current_player):
                print_board(board)
                print(f"\nPlayer {current_player} wins!")
                break

            # Check for draw
            if ' ' not in board:
                print_board(board)
                print("It's a draw!")
                break

            # Switch players
            current_player = 'O' if current_player == 'X' else 'X'

        except ValueError:
            print("Invalid input. Please enter a number.")


if __name__ == "__main__":
    main()
