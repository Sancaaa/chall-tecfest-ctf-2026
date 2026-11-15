package main

import (
	"encoding/binary"
	"math/bits"
)

const (
	flagLen = 58
	h0      = 0x4E414245
	acc0    = 0x5A
	memSize = 64
	insSize = 4
)

type handler func(v *vm, a, b, c byte)

type vm struct {
	code []byte // salinan cipher yang bisa dipatch saat runtime
	mem  [memSize]byte
	st   []byte
	acc  byte
	bad  byte
	nchk int
	pc   int
	h    uint32
	k    byte
	sel  int
	halt bool
	tabs [2][16]handler
}

func newVM(book []byte, input []byte) *vm {
	v := &vm{
		code: append([]byte(nil), book...),
		acc:  acc0,
		h:    h0,
		k:    kA,
		st:   make([]byte, 0, 256),
	}
	v.tabs[0] = tableA()
	v.tabs[1] = tableB()
	copy(v.mem[:], input)
	return v
}

func drift(h, i uint32) uint32 {
	x := h ^ (i * 0x9E3779B1)
	x ^= x >> 16
	x *= 0x85EBCA6B
	x ^= x >> 13
	x *= 0xC2B2AE35
	x ^= x >> 16
	return x
}

func stir(h, w, i uint32) uint32 {
	return bits.RotateLeft32(h^w, 7)*0x01000193 + i
}

func binding(prefix []byte) uint32 {
	key := uint32(0x811C9DC5)
	for _, b := range prefix {
		key = (key ^ uint32(b)) * 0x01000193
	}
	key ^= key >> 16
	key *= 0x7FEB352D
	key ^= key >> 15
	key *= 0x846CA68B
	key ^= key >> 16
	return key
}

func (v *vm) run() bool {
	n := len(v.code) / insSize
	for v.pc < n && !v.halt {
		i := v.pc
		p := i * insSize
		ks := drift(v.h, uint32(i))
		var w [4]byte
		for j := 0; j < 4; j++ {
			w[j] = v.code[p+j] ^ byte(ks>>(8*uint(j)))
		}
		v.h = stir(v.h, binary.LittleEndian.Uint32(w[:]), uint32(i))
		v.pc++
		v.tabs[v.sel][(w[0]^v.k)&15](v, w[1], w[2], w[3])
	}
	return v.bad == 0 && v.nchk == flagLen && v.halt && len(v.st) == 0
}

func (v *vm) push(x byte) {
	if len(v.st) >= 256 {
		v.bad |= 0x80
		return
	}
	v.st = append(v.st, x)
}

func (v *vm) pop() byte {
	n := len(v.st)
	if n == 0 {
		v.bad |= 0x40
		return 0
	}
	x := v.st[n-1]
	v.st = v.st[:n-1]
	return x
}

func (v *vm) rite0(a, b, c byte) { v.push(a) }

func (v *vm) rite1(a, b, c byte) { v.push(v.mem[a&63]) }

func (v *vm) rite2(a, b, c byte) {
	y := v.pop()
	x := v.pop()
	v.push(x + y)
}

func (v *vm) rite3(a, b, c byte) {
	y := v.pop()
	x := v.pop()
	v.push(x - y)
}

func (v *vm) rite4(a, b, c byte) {
	y := v.pop()
	x := v.pop()
	v.push(x ^ y)
}

func (v *vm) rite5(a, b, c byte) {
	x := v.pop()
	r := a & 7
	v.push(x<<r | x>>(8-r))
}

func (v *vm) rite6(a, b, c byte) {
	y := v.pop()
	x := v.pop()
	v.push(x * y)
}

func (v *vm) rite7(a, b, c byte) {
	x := v.pop()
	t := v.acc ^ x
	t = t<<1 | t>>7
	v.acc = t + a
	v.push(v.acc)
}

func (v *vm) rite8(a, b, c byte) {
	x := v.pop()
	v.bad |= x ^ a
	v.nchk++
}

func (v *vm) rite9(a, b, c byte) {
	v.mem[a&63], v.mem[b&63] = v.mem[b&63], v.mem[a&63]
}

func (v *vm) rite10(a, b, c byte) {
	off := int(a) | int(b)<<8
	if off < len(v.code) {
		v.code[off] ^= c
	}
}

func (v *vm) rite11(a, b, c byte) {
	n := int(a)
	if n > memSize {
		n = memSize
	}
	key := binding(v.mem[:n])
	s := key | 1
	for j := v.pc * insSize; j < len(v.code); j++ {
		s ^= s << 13
		s ^= s >> 17
		s ^= s << 5
		v.code[j] ^= byte(s)
	}
}

func (v *vm) rite12(a, b, c byte) {
	v.sel = 1
	v.k = kB
}

func (v *vm) rite13(a, b, c byte) { v.halt = true }

func (v *vm) rite14(a, b, c byte) { v.pop() }

func (v *vm) rite15(a, b, c byte) {}
