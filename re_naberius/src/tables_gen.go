// Dihasilkan oleh gen.py. Jangan diedit manual.
package main

const (
	kA byte = 0x60
	kB byte = 0x5E
)

func tableA() [16]handler {
	return [16]handler{
		(*vm).rite13, // slot  0
		(*vm).rite12, // slot  1
		(*vm).rite8, // slot  2
		(*vm).rite1, // slot  3
		(*vm).rite11, // slot  4
		(*vm).rite3, // slot  5
		(*vm).rite14, // slot  6
		(*vm).rite10, // slot  7
		(*vm).rite15, // slot  8
		(*vm).rite6, // slot  9
		(*vm).rite2, // slot 10
		(*vm).rite9, // slot 11
		(*vm).rite4, // slot 12
		(*vm).rite7, // slot 13
		(*vm).rite0, // slot 14
		(*vm).rite5, // slot 15
	}
}
func tableB() [16]handler {
	return [16]handler{
		(*vm).rite8, // slot  0
		(*vm).rite0, // slot  1
		(*vm).rite9, // slot  2
		(*vm).rite7, // slot  3
		(*vm).rite15, // slot  4
		(*vm).rite1, // slot  5
		(*vm).rite3, // slot  6
		(*vm).rite6, // slot  7
		(*vm).rite12, // slot  8
		(*vm).rite14, // slot  9
		(*vm).rite4, // slot 10
		(*vm).rite10, // slot 11
		(*vm).rite5, // slot 12
		(*vm).rite2, // slot 13
		(*vm).rite13, // slot 14
		(*vm).rite11, // slot 15
	}
}
