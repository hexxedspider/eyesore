import sys
import os
from message_memory import MessageMemory

def clear_memory():
    try:
        memory = MessageMemory()
        memory.clear_memory()
        
        print("Message memory cleared successfully!")
        return True
        
    except Exception as e:
        print(f"Error clearing memory: {e}")
        return False

def show_memory_stats():
    try:
        memory = MessageMemory()
        size = memory.get_memory_size()
        
        print(f"Current memory size: {size} messages")
        
        if size > 0:
            print("Tip: Run this script to clear memory if you're updating personality/lore")
        else:
            print("Memory is already empty")
            
    except Exception as e:
        print(f"Error checking memory stats: {e}")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--stats', '-s']:
            show_memory_stats()
            return
        elif sys.argv[1] in ['--help', '-h']:
            print("Usage: python clear_memory.py [options]")
            print("Options:")
            print("  --stats, -s     Show current memory statistics")
            print("  --help, -h      Show this help message")
            print("  (no args)       Clear memory (default action)")
            return
    
    print("Clearing message memory...")
    print("")
    print("=" * 50)
    print("")
    
    success = clear_memory()
    
    if success:
        pass
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
