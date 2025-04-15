from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use the non-interactive Agg backend
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# Load all season-specific DataFrames and drop the first column
dataframes = {
    "2017/2018": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Data/stats_PL_2017_2018.csv"),
    "2018/2019": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Data/stats_PL_2018_2019.csv"),
    "2019/2020": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Data/stats_PL_2019_2020.csv"),
    "2020/2021": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Data/stats_PL_2020_2021.csv"),
    "2021/2022": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Data/stats_PL_2021_2022.csv"),
    "2022/2023": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Data/stats_PL_2022_2023.csv"),
    "2023/2024": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Data/stats_PL_2023_2024.csv"),
    "2024/2025": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Data/stats_PL_2024_2025.csv"),
}
df_elo = {
    "2017/2018": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Bricks/elo_PL_2017_2018.csv"),
    "2018/2019": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Bricks/elo_PL_2018_2019.csv"),
    "2019/2020": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Bricks/elo_PL_2019_2020.csv"),
    "2020/2021": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Bricks/elo_PL_2020_2021.csv"),
    "2021/2022": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Bricks/elo_PL_2021_2022.csv"),
    "2022/2023": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Bricks/elo_PL_2022_2023.csv"),
    "2023/2024": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Bricks/elo_PL_2023_2024.csv"),
    "2024/2025": pd.read_csv("/Users/howannes/Documents/afthonia/code/Thesis/Bricks/elo_PL_2024_2025.csv"),
}

# Combine all DataFrames into one for player search and "All Time" option
all_seasons_df = pd.concat(
    [df.assign(Season=season) for season, df in dataframes.items()],
    ignore_index=True
)
all_seasons_elo = pd.concat(
    [df.assign(Season=season) for season, df in df_elo.items()],
    ignore_index=True
)

# Default season 
default_season = "2024/2025"

# Route for the homepage
@app.route("/", methods=["GET", "POST"])
def index():
    # Check if the reset button was clicked
    reset_search = request.form.get("reset_search")

    if reset_search:
        # Reset all filters to their default values
        season_filter = default_season
        team_filter = None
        position_filter = None
        player_search = ""
        playing_time_filter = "all"
    else:
        # Get the selected filters from the form
        season_filter = request.form.get("season", default_season)
        team_filter = request.form.get("team")
        position_filter = request.form.get("position")
        player_search = request.form.get("player_search", "").strip()
        playing_time_filter = request.form.get("playing_time_filter", "all")  # Default to "all"

    # Use the selected season's DataFrame or "All Time" DataFrame
    if season_filter == "All Time":
        df = all_seasons_df
    else:
        df = dataframes.get(season_filter, dataframes[default_season])

    # Filter the data based on the selected team and position
    filtered_df = df.copy()
    if team_filter:
        filtered_df = filtered_df[filtered_df["Team"] == team_filter]
    if position_filter:
        filtered_df = filtered_df[filtered_df["Pos"] == position_filter]

    # Apply the playing time filter
    if playing_time_filter == "50_percent":
        # Calculate the total number of games in the season
        total_games = filtered_df["GP"].max()  # Assuming "GP" is the column for games played
        filtered_df = filtered_df[filtered_df["GP"] >= 0.5 * total_games]
    elif playing_time_filter == "5_games":
        filtered_df = filtered_df[filtered_df["GP"] >= 5]

    # Search for player across all seasons
    search_results = None
    if player_search and not reset_search:
        search_results = all_seasons_df[all_seasons_df["Player"].str.contains(player_search, case=False, na=False)]

    # Get unique teams, positions, and seasons for the dropdowns
    teams = sorted(df["Team"].unique())
    positions = sorted(df["Pos"].unique())
    seasons = ["All Time"] + list(dataframes.keys())  # Add "All Time" to the seasons list
    players = sorted(all_seasons_df["Player"].unique())  # Get unique player names

    return render_template(
        "index.html",
        data=filtered_df.to_dict(orient="records"),
        teams=teams,
        positions=positions,
        seasons=seasons,
        selected_season=season_filter,
        selected_team=team_filter,  # Pass the selected team to the template
        selected_position=position_filter,  # Pass the selected position to the template
        search_results=search_results.to_dict(orient="records") if search_results is not None else None,
        player_search=player_search,
        players=players,  # Pass the unique player names to the template
        playing_time_filter=playing_time_filter  # Pass the selected playing time filter to the template
    )

@app.route("/player/<player_name>")
def player_games(player_name):
    # Get the selected season from the request arguments (default to the current season)
    selected_season = request.args.get("season", default_season)

    # Check if the selected season is "All Time"
    if selected_season == "All Time":
        # Use the merged dataset for all seasons
        player_game_data = all_seasons_elo[all_seasons_elo["Player"] == player_name]

        # Check if the player has game data
        if player_game_data.empty:
            return render_template("player_games.html", error=f"No game data found for player: {player_name} across all seasons.")

        # Select only the specified columns
        columns_to_keep = [
            "Season", "Round", "Date", "Venue", "Opponent", "Score", "Start Time", "End Time", 
            "Minutes Played", "Start Result", "End Result", "MOTM", "influence", 
            "Start Elo", "Rating Change", "End Elo"
        ]
        player_game_data = player_game_data[columns_to_keep]
        player_game_data = player_game_data.dropna()

    else:
        # Construct the file path for the selected season
        season_file = f"/Users/howannes/Documents/afthonia/code/Thesis/Bricks/elo_PL_{selected_season.replace('/', '_')}.csv"

        # Try to load the dataset for the selected season
        try:
            season_data = pd.read_csv(season_file)
        except FileNotFoundError:
            return render_template("player_games.html", error=f"Data for season {selected_season} not found.")

        # Filter the data for the selected player
        player_game_data = season_data[season_data["Player"] == player_name]

        # Check if the player has game data
        if player_game_data.empty:
            return render_template("player_games.html", error=f"No game data found for player: {player_name} in season {selected_season}.")

        # Select only the specified columns
        columns_to_keep = [
            "Round", "Date", "Venue", "Opponent", "Score", "Start Time", "End Time", 
            "Minutes Played", "Start Result", "End Result", "MOTM", "influence", 
            "Start Elo",  "Rating Change", "End Elo",
        ]
        player_game_data = player_game_data[columns_to_keep]
        player_game_data = player_game_data.dropna()


    # Round the specified columns to 2 decimal places
    if "Start Elo" in player_game_data.columns:
        player_game_data["Start Elo"] = player_game_data["Start Elo"].round(2)
    if "End Elo" in player_game_data.columns:
        player_game_data["End Elo"] = player_game_data["End Elo"].round(2)
    if "Rating Change" in player_game_data.columns:
        player_game_data["Rating Change"] = player_game_data["Rating Change"].round(2)

    # Convert the filtered data to a dictionary for rendering in the template
    player_game_data = player_game_data.to_dict(orient="records")

    return render_template("player_games.html", player_name=player_name, games=player_game_data, season=selected_season)


@app.route("/compare", methods=["POST"])
def compare_players():
    # Get the input from the form and split it into a list of player names
    players_input = request.form.get("players", "")
    selected_players = [player.strip() for player in players_input.split(",") if player.strip()]

    # Check if any players were entered
    if not selected_players:
        return render_template("compare_players.html", error="No players entered. Please try again.")

    # Filter the data for the selected players
    comparison_data = all_seasons_df[all_seasons_df["Player"].isin(selected_players)]

    # Check if any of the entered players exist in the dataset
    if comparison_data.empty:
        return render_template("compare_players.html", error="No matching players found. Please check the names and try again.")

    # Create the comparison plot
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))  # Create a grid of plots (2 rows, 4 columns)
    stats = ["AdjPPG", "Win_pct", "End Elo", "relDelta", "EPG", "teamRank", "Market Value"]
    for i, stat in enumerate(stats):
        row, col = divmod(i, 4)
        for player in selected_players:
            player_data = comparison_data[comparison_data["Player"] == player]
            axes[row, col].plot(player_data["Season"], player_data[stat], marker="o", label=player)
        axes[row, col].set_title(stat)
        axes[row, col].set_xlabel("Season")
        axes[row, col].set_ylabel(stat)
        axes[row, col].legend()
        axes[row, col].grid(True)

    # Remove any empty subplots
    for i in range(len(stats), 8):
        row, col = divmod(i, 4)
        fig.delaxes(axes[row, col])

    plt.tight_layout()

    # Convert the plot to a PNG image
    img = io.BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode("utf8")
    plt.close()

    return render_template("compare_players.html", selected_players=selected_players, plot_url=plot_url)

if __name__ == "__main__":
    app.run(debug=True)