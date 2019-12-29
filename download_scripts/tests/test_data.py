import pytest
import zipfile

__author__ = 'Stephen Diehl'

import numpy as np
from .. import data_helper as dh


def test_lahman_download(data_dir):
    lahman_dir = data_dir / 'lahman'
    raw_dir = lahman_dir / 'raw'
    wrangled_dir = lahman_dir / 'wrangled'

    assert lahman_dir.is_dir()
    assert wrangled_dir.is_dir()
    assert raw_dir.is_dir()

    # 2 directories and 1 file
    assert len(list(lahman_dir.iterdir())) == 3

    # zip from master branch of https://github.com/chadwickbureau/baseballdatabank
    zipfilename = raw_dir.joinpath('baseballdatabank-master.zip')
    assert zipfilename.is_file()

    zipped = zipfile.ZipFile(zipfilename)
    zip_core_files = [file for file in zipped.namelist()
                      if file.startswith('baseballdatabank-master/core/') and
                      file.endswith('.csv')]

    # each csv file in the zipfile should be in raw_dir
    assert len(list(raw_dir.glob('*.csv'))) == len(zip_core_files)


def test_retrosheet_download(data_dir):
    """Verify data downloaded and unzipped."""
    retrosheet_dir = data_dir / 'retrosheet'
    raw_dir = retrosheet_dir / 'raw'
    wrangled_dir = retrosheet_dir / 'wrangled'

    assert retrosheet_dir.is_dir()
    assert wrangled_dir.is_dir()
    assert raw_dir.is_dir()

    teams = raw_dir.glob('TEAM*')
    years = sorted([team.name[4:] for team in teams])

    for year in years:
        zipdata = raw_dir.joinpath(f'{year}eve.zip')
        assert zipdata.exists()

        # should be same number of files in raw_dir as in zipfile
        files = [file for file in raw_dir.glob(f'*{year}*') if not file.name.endswith('.zip')]
        zipped = zipfile.ZipFile(zipdata)
        assert len(files) == len(zipped.namelist())


def test_lahman_people_pkey(data_dir):
    filename = data_dir / 'lahman' / 'wrangled' / 'people.csv'

    # check for duplicate IDs
    people = dh.from_csv_with_types(filename)
    assert dh.is_unique(people, ['player_id'])  # lahman player id
    assert dh.is_unique(people, ['retro_id'], ignore_null=True)  # retrosheet player id


def test_lahman_fielding_pkey(data_dir):
    filename = data_dir / 'lahman' / 'wrangled' / 'fielding.csv'

    # check for duplicate IDs
    fielding = dh.from_csv_with_types(filename)
    assert dh.is_unique(fielding, ['player_id', 'year_id', 'stint', 'team_id', 'pos'])


def test_lahman_batting_pkey(data_dir):
    filename = data_dir / 'lahman' / 'wrangled' / 'batting.csv'

    # check for duplicate IDs
    batting = dh.from_csv_with_types(filename)
    assert dh.is_unique(batting, ['player_id', 'year_id', 'stint', 'team_id'])


def test_lahman_pitching_pkey(data_dir):
    filename = data_dir / 'lahman' / 'wrangled' / 'pitching.csv'

    # check for duplicate IDs
    pitching = dh.from_csv_with_types(filename)
    assert dh.is_unique(pitching, ['player_id', 'year_id', 'stint', 'team_id'])


def test_lahman_salaries_pkey(data_dir):
    filename = data_dir / 'lahman' / 'wrangled' / 'salaries.csv'

    # check for duplicate IDs
    salaries = dh.from_csv_with_types(filename)
    assert dh.is_unique(salaries, ['player_id', 'year_id', 'team_id'])


def test_lahman_teams_pkey(data_dir):
    filename = data_dir / 'lahman' / 'wrangled' / 'teams.csv'

    # check for duplicate IDs
    teams = dh.from_csv_with_types(filename)
    assert dh.is_unique(teams, ['team_id', 'year_id'])  # lahman team_id
    assert dh.is_unique(teams, ['team_id_retro', 'year_id'])  # retrosheet team_id


def test_lahman_parks_pkey(data_dir):
    filename = data_dir / 'lahman' / 'wrangled' / 'parks.csv'

    # check for duplicate IDs
    parks = dh.from_csv_with_types(filename)
    assert dh.is_unique(parks, ['park_key'])

    # park_name is not unique
    # assert dh.is_unique(parks, ['park_name']


@pytest.mark.slow
def test_player_game_id_values(player_game):
    # note: test is not slow, but running the session fixture could take 30 seconds
    filt = player_game['home_fl'] == 0
    player_game['home_team_id'] = player_game['team_id']
    player_game.loc[filt, 'home_team_id'] = player_game.loc[filt, 'opponent_id']

    assert (player_game['game_id'] == player_game['home_team_id'] +
            player_game['game_dt'].astype(str) + player_game['game_ct'].astype(str)).all()


def test_batting_pkey(batting):
    assert dh.is_unique(batting, ['player_id', 'game_id'])


def test_pitching_pkey(pitching):
    assert dh.is_unique(pitching, ['player_id', 'game_id'])


def test_fielding_pkey(fielding):
    assert dh.is_unique(fielding, ['player_id', 'game_id', 'pos'])


def test_team_game_pkey(team_game):
    assert dh.is_unique(team_game, ['team_id', 'game_id'])


def test_game_pkey(game):
    assert dh.is_unique(game, ['game_id'])


def test_lahman_retro_batting_data(data_dir, batting):
    """Compare Aggregated Lahman batting data to Aggregated Retrosheet batting data

    The scripts must have worked correctly if the 16 batting fields
    in common have almost exactly the same sum between 1974 and 2019
    """
    filename = data_dir / 'lahman' / 'wrangled' / 'batting.csv'
    lahman_batting = dh.from_csv_with_types(filename)

    # Retrosheet data has no missing games since 1974
    filt = (lahman_batting['year_id'] >= 1974) & (lahman_batting['year_id'] <= 2019)
    l_batting = lahman_batting[filt]

    filt = (batting['game_id'].str[3:7] >= '1974') & (batting['game_id'].str[3:7] <= '2019')
    r_batting = batting.loc[filt]

    # columns in common -- these are the columns to compare
    b_cols = set(batting.columns) & set(lahman_batting.columns)
    b_cols -= {'player_id'}

    # there are 16 columns in common
    assert len(b_cols) == 16

    l_batting = l_batting[b_cols]
    r_batting = r_batting[b_cols]

    l_sums = l_batting.agg('sum').astype(int)
    r_sums = r_batting.agg('sum').astype(int)

    # verify all 16 batting attributes from 1974-2019
    # are within plus/minus 0.01% of each other when summed
    assert (np.abs(1.0 - (l_sums / r_sums)) < .0001).all()


def test_lahman_retro_pitching_data(data_dir, pitching):
    """Compare Aggregated Lahman pitching data to Aggregated Retrosheet pitching data

    The scripts must have worked correctly if the 19 pitching fields
    in common have almost exactly the same sum between 1974 and 2019
    """
    filename = data_dir / 'lahman' / 'wrangled' / 'pitching.csv'
    lahman_pitching = dh.from_csv_with_types(filename)

    # Retrosheet data has no missing games since 1974
    filt = (lahman_pitching['year_id'] >= 1974) & (lahman_pitching['year_id'] <= 2019)
    l_pitching = lahman_pitching[filt]

    filt = (pitching['game_id'].str[3:7] >= '1974') & (pitching['game_id'].str[3:7] <= '2019')
    r_pitching = pitching.loc[filt]

    # columns in common -- these are the columns to compare
    p_cols = set(l_pitching.columns) & set(r_pitching.columns)
    p_cols -= {'player_id'}

    # there are 19 columns in common
    assert len(p_cols) == 19

    l_pitching = l_pitching[p_cols]
    r_pitching = r_pitching[p_cols]

    l_sums = l_pitching.agg('sum').astype(int)
    r_sums = r_pitching.agg('sum').astype(int)

    # verify all values between 1974 and 2019 are within plus/minus 0.06% of each other
    assert (np.abs(1.0 - (l_sums / r_sums)) < .0006).all()


def test_lahman_retro_fielding_data(data_dir, fielding):
    """Compare Aggregated Lahman fielding per position data to
    Aggregated Retrosheet fielding per position data

    The scripts must have worked correctly if the 7 fielding fields
    in common have almost exactly the same sum between 1974 and 2019
    for every position.
    """
    filename = data_dir / 'lahman' / 'wrangled' / 'fielding.csv'
    lahman_fielding = dh.from_csv_with_types(filename)

    # Retrosheet data has no missing games since 1974
    filt = (lahman_fielding['year_id'] >= 1974) & (lahman_fielding['year_id'] <= 2019)
    l_fielding = lahman_fielding[filt]

    filt = (fielding['game_id'].str[3:7] >= '1974') & (fielding['game_id'].str[3:7] <= '2019')
    r_fielding = fielding.loc[filt]

    r_fielding = r_fielding.rename(columns={'out': 'inn_outs'})

    # find the common columns
    f_cols = (set(l_fielding.columns) & set(r_fielding.columns)) - set(['player_id', 'pos'])
    f_cols = list(f_cols)

    l_sums = l_fielding.groupby('pos')[f_cols].aggregate('sum')
    l_sums.sort_index(inplace=True)

    # change position values to be lower case
    idxs = {idx: idx.lower() for idx in l_sums.index}
    l_sums.rename(index=idxs, inplace=True)

    # there are 7 fielding attributes and 7 fielding positions in Lahman
    assert l_sums.shape == (7, 7)

    r_sums = r_fielding.groupby('pos')[f_cols].aggregate('sum').astype('int')

    # Lahman uses OF for sum of LF, CF, RF
    r_sums.loc['of'] = r_sums.loc['lf'] + r_sums.loc['cf'] + r_sums.loc['rf']
    r_sums = r_sums.drop(['lf', 'cf', 'rf'])
    r_sums.sort_index(inplace=True)

    # there are 7 fielding attributes and 7 fielding positions in Retrosheet
    assert r_sums.shape == (7, 7)

    # the indexes and columns should now be the same
    assert l_sums.index.equals(r_sums.index)
    assert l_sums.columns.equals(r_sums.columns)

    #
    # # verify all values between 1974 and 2019 are within plus/minus 0.06% of each other
    # assert (np.abs(1.0 - (l_sums / r_sums)) < .0006).all()
