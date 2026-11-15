package main

import (
	"bufio"
	_ "embed"
	"fmt"
	"os"
	"strings"
)

//go:embed book.bin
var book []byte

func verify(input []byte) (ok bool) {
	defer func() {
		if recover() != nil {
			ok = false
		}
	}()
	return newVM(book, input).run()
}

func main() {
	fmt.Println("=== Naberius, the Chained Book of Life ===")
	fmt.Println("Each page is sealed by the one before it.")
	fmt.Print("Speak thy name, witch: ")

	line, _ := bufio.NewReader(os.Stdin).ReadString('\n')
	line = strings.TrimRight(line, "\r\n")

	if len(line) == flagLen && verify([]byte(line)) {
		fmt.Println("The Book of Life writes thy name. So it is.")
		return
	}
	fmt.Println("The Book remains closed.")
	os.Exit(1)
}
