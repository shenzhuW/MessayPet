# main.py
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from core import (
    ConfigManager,
    AnimationManager,
    PhysicsEngine,
    StatManager,
    EventBus,
    EventType,
    PetWindow,
    WindowTracker,
)
from ui.tray_manager import TrayManager
from systems.ai import LLMClient, LLMConfig


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Initialize core services
    event_bus = EventBus()
    config_manager = ConfigManager()
    stat_manager = StatManager()
    animation_manager = AnimationManager()
    physics = PhysicsEngine()

    # Load saved stats
    saved_stats = config_manager.load_stats()
    if saved_stats:
        stat_manager = StatManager.from_dict(saved_stats)

    # Initialize AI (requires ANTHROPIC_API_KEY env var)
    llm_config = LLMConfig()
    llm_client = LLMClient(llm_config)

    # Load default skin
    default_skin = "skins/default"
    if os.path.exists(default_skin):
        animation_manager.load_idle_sequence(default_skin)

    # Window tracking
    window_tracker = WindowTracker(pet_size=(64, 64), event_bus=event_bus)

    # Create pet window with event bus
    pet = PetWindow(
        config_manager=config_manager,
        animation_manager=animation_manager,
        stat_manager=stat_manager,
        event_bus=event_bus,
        window_tracker=window_tracker,
        llm_client=llm_client,
    )
    pet.show()

    # 托盘管理器
    tray_manager = TrayManager()
    tray_manager.setup(pet_window=pet)
    tray_manager.quit_requested.connect(lambda: cleanup_and_quit(app, pet, config_manager, window_tracker))

    def cleanup_and_quit(application, pet_window, config_mgr, tracker):
        """退出前清理资源"""
        # 保存位置
        config_mgr.save_position(pet_window.x(), pet_window.y())
        # 停止追踪
        if tracker:
            tracker.stop_tracking()
        # 退出应用
        application.quit()

    # Stat decay timer (every second)
    stat_timer = QTimer()
    stat_timer.timeout.connect(lambda: stat_manager.tick(1.0))
    stat_timer.start(1000)

    # Save stats periodically (every 30 seconds)
    save_timer = QTimer()
    save_timer.timeout.connect(lambda: config_manager.save_stats(stat_manager.to_dict()))
    save_timer.start(30000)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()