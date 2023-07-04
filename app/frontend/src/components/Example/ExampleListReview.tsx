import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    { text: "What are the top 10 topics since 2023-01-01?", value: "What are the top 10 topics since 2023-01-01?" },
    { text: "what's the new topics in version 5.43.1 but not in other versions?", value: "what's the new topics in version 5.43.1 but not in other versions?" },
    {
        text: "Show me the reviews that has 'login error' in the topics since 2023-01-01?",
        value: "Show me the reviews that has 'login error' in the topics since 2023-01-01."
    }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
