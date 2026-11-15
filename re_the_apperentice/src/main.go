package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

const (
	opLoad    byte = 0x01
	opXor     byte = 0x02
	opAddIdx  byte = 0x03
	opCmp     byte = 0x04
	opNext    byte = 0x05
	opSuccess byte = 0x06
	opFail    byte = 0x07
)

// String literals stay in .rodata without runtime slice initialization.
var spellBytecode = "\x01\x02\x5a\x03\x04\x05\x06\x07"
var spellTarget = "\x0e\x40\x3b\x1f\x43\x2e\x34\x6f\x74\x2a\x47\x75\x11\x39\x45\x14\x7e\x3b\x3c\x3b\x7d\x49\x44\x82\x51\x82\x1f\x58\x44\x88\x55\x89\x8b\x49\x8b\x4a"

// Prevent inlining so main.executeVM remains a distinct symbol for static analysis.
//
//go:noinline
func executeVM(input string) bool {
	if len(input) != len(spellTarget) {
		return false
	}

	pc := 0
	idx := 0
	var acc byte

	for pc < len(spellBytecode) {
		switch spellBytecode[pc] {
		case opLoad:
			acc = input[idx]
			pc++
		case opXor:
			pc++
			if pc >= len(spellBytecode) {
				return false
			}
			acc ^= spellBytecode[pc]
			pc++
		case opAddIdx:
			acc += byte(idx)
			pc++
		case opCmp:
			if acc != spellTarget[idx] {
				return false
			}
			pc++
		case opNext:
			idx++
			if idx >= len(spellTarget) {
				pc++
			} else {
				pc = 0
			}
		case opSuccess:
			return true
		case opFail:
			return false
		default:
			return false
		}
	}

	return false
}

func main() {
	fmt.Println("=== The Apprentice Grimoire ===")
	fmt.Print("Speak the incantation: ")

	reader := bufio.NewReader(os.Stdin)
	line, err := reader.ReadString('\n')
	if err != nil && len(line) == 0 {
		fmt.Println("The spell fizzles.")
		return
	}

	input := strings.TrimRight(line, "\r\n")
	if executeVM(input) {
		fmt.Println("The spell holds!")
	} else {
		fmt.Println("The spell fizzles.")
	}
}
