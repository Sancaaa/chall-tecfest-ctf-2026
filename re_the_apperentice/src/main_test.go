package main

import "testing"

func TestExecuteVM(t *testing.T) {
	validFlag := "TecFest26{g0_vm_4ppr3nt1c3_gr1m01r3}"
	if !executeVM(validFlag) {
		t.Fatalf("expected valid flag %q to pass", validFlag)
	}

	cases := []struct {
		name  string
		input string
	}{
		{"empty", ""},
		{"too short", "TecFest26{short}"},
		{"too long", validFlag + "extra"},
		{"wrong first char", "XecFest26{g0_vm_4ppr3nt1c3_gr1m01r3}"},
		{"wrong last char", "TecFest26{g0_vm_4ppr3nt1c3_gr1m01r3!"},
		{"wrong middle char", "TecFest26{g0_vm_4ppr3nt1c3_gr1m01r4}"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if executeVM(tc.input) {
				t.Fatalf("expected %q to fail", tc.input)
			}
		})
	}
}

func TestBytecodeAndTargetIntegrity(t *testing.T) {
	if len(spellBytecode) != 8 {
		t.Fatalf("unexpected bytecode length: got %d, want 8", len(spellBytecode))
	}
	if len(spellTarget) != 36 {
		t.Fatalf("unexpected target length: got %d, want 36", len(spellTarget))
	}
}
