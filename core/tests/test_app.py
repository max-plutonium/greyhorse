from greyhorse.app.entities.application import Application


def test_load_module():
    app = Application(name='TestApp')

    res = app.load('tests.app.main', {'id': 123, 'data': 'test0'})
    assert res.success

    res = app.create()
    assert not res

    app.start()

    with app.graceful_exit():
        app.run_sync()

    app.stop()

    res = app.destroy()
    assert not res

    res = app.unload()
    assert res.success
