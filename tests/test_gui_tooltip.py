from conftest import HasHint


def test_a_hint_appears_over_a_disabled_button(Root, MakeButton):
    # Abort spends most of its life greyed, and that is exactly when the hint is needed.
    from generalsmodbuilder.gui.layout import Tooltip

    button = MakeButton("disabled")
    tip = Tooltip(button, "Stops the running game.", delayMs=1)
    assert tip.window is None

    button.event_generate("<Enter>", x=2, y=2)
    Root.update()
    Root.after(20)
    Root.update()
    assert tip.window is not None, "no hint appeared while the pointer rested on the button"

    button.event_generate("<Leave>")
    Root.update()
    assert tip.window is None, "the hint outlived the pointer"


def test_leaving_before_the_delay_shows_nothing(Root, MakeButton):
    from generalsmodbuilder.gui.layout import Tooltip

    button = MakeButton()
    tip = Tooltip(button, "Stops the running game.", delayMs=5000)

    button.event_generate("<Enter>", x=2, y=2)
    Root.update()
    button.event_generate("<Leave>")
    Root.update()

    assert tip.window is None
    assert tip.timer is None


def test_a_hint_is_visible_to_the_tests_that_look_for_one(MakeButton):
    from generalsmodbuilder.gui.layout import Tooltip

    bare = MakeButton()
    assert not HasHint(bare)

    hinted = MakeButton()
    Tooltip(hinted, "Stops the running game.")
    assert HasHint(hinted)
