// Tailwind configuration moved out of template to avoid CSP/inline-script issues
if (typeof tailwind !== 'undefined') {
    tailwind.config = {
        theme: {
            extend: {
                colors: {
                    slate: {
                        850: '#1a2332',
                    }
                },
                fontFamily: {
                    sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
                }
            }
        }
    }
}
