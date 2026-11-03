from src.paths import DATA, QUESTIONS, RESULTS, ROOT


def test_project_paths_exist():
    assert ROOT.exists()
    assert DATA.exists()
    assert QUESTIONS.exists()
    assert RESULTS.exists()

